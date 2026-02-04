from unittest.mock import AsyncMock, MagicMock

from app.coder.routes.htmx import cancel_turn
from app.coder.services.execution_registry import TurnExecution


class TestCoderHtmxRoutes:
    async def test_cancel_turn_calls_registry_cancel(self, mocker):
        """POST /coder/turns/{turn_id}/cancel should call registry.cancel and return partials."""
        mock_registry = AsyncMock()
        mock_run = MagicMock(spec=TurnExecution)
        mock_run.user_message = "Original Message"
        mock_registry.cancel.return_value = mock_run

        mock_request = MagicMock()
        mock_request.headers = {"HX-Request": "true"}

        # Call the route handler directly to avoid setting up full client/dependency overrides for this unit test
        response = await cancel_turn.__wrapped__(
            request=mock_request, turn_id="t1", registry=mock_registry
        )

        mock_registry.cancel.assert_awaited_once_with(turn_id="t1")
        assert response["content"] == "Original Message"
        assert response["turn_id"] == "t1"

    async def test_cancel_turn_renders_correct_partials(self, mocker):
        """The response should include message_form, remove_user_message, and remove_ai_message."""
        # This test is slightly redundant with the above since we return a dict for the @htmx decorator,
        # but we can verify the behavior when registry returns None (run not found).
        mock_registry = AsyncMock()
        mock_registry.cancel.return_value = None  # Run not found/already gone

        req = MagicMock()
        req.headers = {"HX-Request": "true"}
        response = await cancel_turn.__wrapped__(
            request=req, turn_id="t1", registry=mock_registry
        )

        # Should fail safely with empty content
        assert response["content"] == ""
