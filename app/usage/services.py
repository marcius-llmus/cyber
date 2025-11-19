from app.usage.schemas import SessionMetrics


class UsageService:
    def __init__(self):
        # This will later depend on a repository for persistence
        # For now, it holds metrics in memory for the app's lifetime.
        self._total_cost = 0.0
        self._input_tokens = 0
        self._output_tokens = 0

        # Simple cost model (example for Gemini Flash)
        self.cost_per_input_token = 0.00000035  # $0.35 / 1M tokens
        self.cost_per_output_token = 0.00000053  # $0.53 / 1M tokens

    async def add_llm_usage(self, input_tokens: int, output_tokens: int) -> SessionMetrics:
        """Adds LLM token usage and recalculates the total cost."""
        cost = (input_tokens * self.cost_per_input_token) + (
            output_tokens * self.cost_per_output_token
        )
        self._total_cost += cost
        self._input_tokens += input_tokens
        self._output_tokens += output_tokens
        return await self.get_session_metrics()

    async def get_session_metrics(self) -> SessionMetrics:
        return SessionMetrics(
            session_cost=self._total_cost,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
        )


class UsagePageService:
    def __init__(self, usage_service: UsageService):
        self.usage_service = usage_service

    async def get_session_metrics_page_data(self) -> dict:
        metrics = await self.usage_service.get_session_metrics()
        return {"metrics": metrics.model_dump()}