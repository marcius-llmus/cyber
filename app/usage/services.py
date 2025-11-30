import logging
from typing import Any
from decimal import Decimal

from pydantic.alias_generators import to_camel
# extract_usage is not in __all__ by some reason
from genai_prices import extract_usage, calc_price # noqa

from app.usage.schemas import SessionMetrics
from app.usage.repositories import UsageRepository, GlobalUsageRepository
from app.llms.factories import LLMFactory
from app.llms.enums import LLMModel
from app.settings.services import SettingsService

logger = logging.getLogger(__name__)


class UsageService:
    def __init__(
        self,
        usage_repo: UsageRepository,
        global_usage_repo: GlobalUsageRepository,
        llm_factory: LLMFactory,
        settings_service: SettingsService
    ):
        self.usage_repo = usage_repo
        self.global_usage_repo = global_usage_repo
        self.llm_factory = llm_factory
        self.settings_service = settings_service

    async def process_workflow_usage(self, session_id: int, response: Any) -> SessionMetrics:
        """
        Extracts usage from response, updates DBs, and returns the event.
        """
        # 1. Resolve Model & Adapter
        settings = await self.settings_service.get_settings()
        model_name = LLMModel(settings.coding_llm_settings.model_name)
        llm_meta = await self.llm_factory.get_llm(model_name)

        # 2. Extract Usage & Calculate Cost
        try:
            # genai-prices expects lowercase provider id
            provider_id = llm_meta.provider.value.lower()

            raw_data = self._normalize_raw_data(response.raw)
            # Use genai-prices to extract usage and calculate price
            extraction_data = extract_usage(raw_data, provider_id=provider_id)
            usage_data = extraction_data.usage
            # btw, the example at https://github.com/pydantic/genai-prices/blob/main/packages/python/README.md
            # didn't work very well. model was not present if calc_price was called from extract_usage
            price_data = calc_price(usage_data, model_ref=model_name, provider_id=provider_id) # noqa

            cost = Decimal(str(price_data.total_price))
            
            input_tokens = usage_data.input_tokens or 0
            output_tokens = usage_data.output_tokens or 0
            cached_tokens = usage_data.cache_read_tokens or 0

            logger.debug(
                f"Usage Extracted [Session={session_id}]: {provider_id}/{model_name} | "
                f"Cost=${cost:.6f} | Tokens: In={input_tokens}, Out={output_tokens}, Cache={cached_tokens}"
            )
            
        except Exception as e:
            logger.warning(f"Failed to calculate usage metrics: {e}")
            return SessionMetrics()

        # 4. Update DBs
        session_usage = await self.usage_repo.increment_usage(
            session_id, cost, input_tokens, output_tokens, cached_tokens
        )
        global_usage = await self.global_usage_repo.increment_provider_usage(
            llm_meta.provider, cost, input_tokens, output_tokens, cached_tokens
        )
        
        logger.debug(
            f"DB Updated: Session {session_id} Total=${session_usage.cost:.6f} | "
            f"Global ({llm_meta.provider}) Total=${global_usage.total_cost:.6f}"
        )

        # Calculate total global cost across all providers
        total_global_cost = await self.global_usage_repo.get_total_global_cost()

        # 5. Return Metrics
        return SessionMetrics(
            session_cost=session_usage.cost,
            monthly_cost=float(total_global_cost),
            input_tokens=session_usage.input_tokens,
            output_tokens=session_usage.output_tokens,
            cached_tokens=session_usage.cached_tokens
        )

    async def get_session_metrics(self, session_id: int) -> SessionMetrics:
        usage = await self.usage_repo.get_by_session_id(session_id)
        total_global_cost = await self.global_usage_repo.get_total_global_cost()
        if not usage:
            return SessionMetrics(monthly_cost=float(total_global_cost))
            
        return SessionMetrics(
            session_cost=usage.cost,
            monthly_cost=float(total_global_cost),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens
        )

    @staticmethod
    def _normalize_raw_data(data: Any) -> Any:
        """
        Converts the raw response object into a dictionary with camelCase keys.
        This is necessary because the `genai_prices` library expects the raw API response format (camelCase),
        but Python SDKs (and Pydantic models) often use snake_case.
        """

        def _recursive_to_camel(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {to_camel(k): _recursive_to_camel(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_recursive_to_camel(i) for i in obj]
            return obj

        return _recursive_to_camel(data)


class UsagePageService:
    def __init__(self, usage_service: UsageService, session_id: int = 0):
        self.usage_service = usage_service
        self.session_id = session_id

    async def get_session_metrics_page_data(self) -> dict:
        metrics = await self.usage_service.get_session_metrics(self.session_id)
        return {"metrics": metrics.model_dump()}