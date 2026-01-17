import logging
from decimal import Decimal
from typing import Any

# extract_usage is not in __all__ by some reason
from genai_prices import calc_price, extract_usage  # noqa
from llama_index.core.instrumentation.events import BaseEvent
from pydantic import BaseModel
from pydantic.alias_generators import to_camel

from app.llms.services import LLMService
from app.settings.services import SettingsService
from app.usage.exceptions import UsageTrackingException
from app.usage.repositories import GlobalUsageRepository, UsageRepository
from app.usage.schemas import SessionMetrics

logger = logging.getLogger(__name__)


class UsageService:
    def __init__(
        self,
        usage_repo: UsageRepository,
        global_usage_repo: GlobalUsageRepository,
        llm_service: LLMService,
        settings_service: SettingsService,
    ):
        self.usage_repo = usage_repo
        self.global_usage_repo = global_usage_repo
        self.llm_service = llm_service
        self.settings_service = settings_service

    async def track_event(self, session_id: int, event: BaseEvent) -> None:
        """Process a single usage event and update repositories."""
        try:
            if getattr(event, "response", None) is None:
                raise ValueError(f"Event {type(event)} response is None or missing.")

            # 1. Extract Identity from Event Tags (Injected by InstrumentedLLMMixin)
            if not (tags := event.tags):
                raise ValueError(
                    "Event tags are missing. Ensure InstrumentedLLM is being used."
                )

            provider_id = tags["__provider_id__"]
            model_name = tags["__model_name__"]
            flavor = tags["__api_flavor__"]

            if not provider_id or not model_name:
                raise ValueError(
                    "Event missing required instrumentation tags (__provider_id__, __model_name__)."
                )

            cost, input_t, output_t, cached_t = await self._calculate_event_usage(
                event, provider_id, model_name, flavor
            )

            await self._update_usage_repositories(
                session_id, provider_id, cost, input_t, output_t, cached_t
            )
        except Exception as e:
            raise UsageTrackingException(
                f"Failed to track usage event: {str(e)}"
            ) from e

    async def process_batch(
        self, session_id: int, events: list[BaseEvent]
    ) -> SessionMetrics:
        """
        Processes a batch of raw instrumentation events.
        Updates costs and returns the final calculated metrics for the session.
        """
        errors = []
        if events:
            for event in events:
                try:
                    await self.track_event(session_id, event)
                except UsageTrackingException as e:
                    logger.error(f"Usage tracking failed for event {type(event)}: {e}")
                    errors.append(str(e))

        metrics = await self.get_session_metrics(session_id)
        metrics.errors = errors
        return metrics

    async def _update_usage_repositories(
        self,
        session_id: int,
        provider_name: str,
        cost: Decimal,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
    ) -> SessionMetrics:
        session_usage = await self.usage_repo.increment_usage(
            session_id, cost, input_tokens, output_tokens, cached_tokens
        )

        global_usage = await self.global_usage_repo.increment_provider_usage(
            provider_name, cost, input_tokens, output_tokens, cached_tokens
        )

        logger.debug(
            f"DB Updated: Session {session_id} Total=${session_usage.cost:.6f} | "
            f"Global ({provider_name}) Total=${global_usage.total_cost:.6f}"
        )

        total_global_cost = await self.global_usage_repo.get_total_global_cost()

        return SessionMetrics(
            session_cost=session_usage.cost,
            monthly_cost=float(total_global_cost),
            input_tokens=session_usage.input_tokens,
            output_tokens=session_usage.output_tokens,
            cached_tokens=session_usage.cached_tokens,
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
            cached_tokens=usage.cached_tokens,
        )

    async def _calculate_event_usage(
        self, event, provider_id: str, model_ref: str, flavor: str
    ) -> tuple[Decimal, int, int, int]:
        """
        Helper to extract usage from a single response object using existing logic.
        Returns (cost, input_tokens, output_tokens, cached_tokens).
        """
        raw_data = self._normalize_raw_data(event.response.raw, flavor)
        # Use genai-prices to extract usage and calculate price
        extraction_data = extract_usage(
            raw_data, provider_id=provider_id, api_flavor=flavor
        )
        usage_data = extraction_data.usage
        # btw, the example at https://github.com/pydantic/genai-prices/blob/main/packages/python/README.md
        # didn't work very well. model was not present if calc_price was called from extract_usage
        price_data = calc_price(
            usage_data, model_ref=model_ref, provider_id=provider_id
        )  # noqa

        cost = Decimal(str(price_data.total_price))

        input_tokens = usage_data.input_tokens or 0
        output_tokens = usage_data.output_tokens or 0
        cached_tokens = usage_data.cache_read_tokens or 0

        return cost, input_tokens, output_tokens, cached_tokens

    @staticmethod
    def _normalize_raw_data(data: dict | BaseModel, flavor) -> Any:
        """
        Converts the raw response object into a dictionary with camelCase keys.
        This is necessary because the `genai_prices` library expects the raw API response format (camelCase),
        But for openai for example, which uses chat flavor, it is snake_case
        but Python SDKs (and Pydantic models) often use snake_case.
        """

        if isinstance(data, BaseModel):
            data = data.model_dump()

        # bruh, different flavors have different cases :c
        if flavor != "default":
            return data

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

    async def get_empty_metrics_page_data(self) -> dict:
        metrics = await self.usage_service.get_session_metrics(0)
        return {"metrics": metrics.model_dump()}
