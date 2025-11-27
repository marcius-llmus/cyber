import logging
import uuid
from typing import Any, Callable, Coroutine

from fastapi import WebSocketDisconnect
from pydantic import ValidationError

from app.coder.services import CoderService
from app.coder.schemas import (
    AIMessageChunkEvent,
    AIMessageCompletedEvent,
    CoderEvent,
    UsageMetricsUpdatedEvent,
    WebSocketMessage,
    WorkflowErrorEvent,
    WorkflowLogEvent,
    LogLevel,
)
from app.commons.websockets import WebSocketConnectionManager
from app.core.templating import templates
from datetime import datetime

logger = logging.getLogger(__name__)

Handler = Callable[..., Coroutine[Any, Any, None]]


class WebSocketOrchestrator:
    def __init__(
        self,
        ws_manager: WebSocketConnectionManager,
        session_id: int,
        coder_service: CoderService,
    ):
        self.ws_manager = ws_manager
        self.session_id = session_id
        self.coder_service = coder_service
        self.event_handlers: dict[type, Handler] = {
            AIMessageChunkEvent: self._render_ai_message_chunk,
            AIMessageCompletedEvent: self._render_ai_message_controls,
            WorkflowErrorEvent: self._render_workflow_error,
            UsageMetricsUpdatedEvent: self._render_usage_metrics,
            WorkflowLogEvent: self._handle_workflow_log,
        }

    async def _process_event(self, event: CoderEvent, turn_id: str):
        # todo check later if it is okay to get by klass type directly
        handler = self.event_handlers.get(type(event))
        if not handler:
            logger.warning(f"No handler for event type: {type(event)}")
            return
        await handler(event, turn_id=turn_id)

    async def _prepare_ui_for_new_turn(self, message_content: str) -> str:
        turn_id = str(uuid.uuid4())
        await self._render_user_message(message_content, turn_id)
        await self._render_ai_bubble_placeholder(turn_id)
        return turn_id

    async def _prepare_ui_for_retry_turn(self, turn_id: str) -> str:
        await self._render_ai_bubble_placeholder(turn_id)
        await self._remove_user_message_controls(turn_id)
        return turn_id

    async def handle_connection(self):
        logger.info("WebSocket connection established.")

        try:
            while True:
                data = await self.ws_manager.receive_json()
                logger.info("Received JSON data from client.")

                try:
                    message = WebSocketMessage(**data)
                except ValidationError as e:
                    logger.error(f"WebSocket validation error: {e}", exc_info=True)
                    await self._render_error(f"Invalid message format: {e}")
                    continue

                if retry_turn_id := data.get("retry_turn_id"):
                    turn_id = await self._prepare_ui_for_retry_turn(retry_turn_id)
                else:
                    turn_id = await self._prepare_ui_for_new_turn(message.message)

                try:
                    stream = self.coder_service.handle_user_message(
                        user_message=message.message, session_id=self.session_id
                    )

                    async for event in stream:
                        await self._process_event(event, turn_id)

                except Exception as e:
                    logger.error(f"An error occurred in WebSocket turn {turn_id}: {e}", exc_info=True)
                    await self._render_workflow_error(event=WorkflowErrorEvent(message=str(e), original_message=message.message), turn_id=turn_id)

        except WebSocketDisconnect:
            logger.info("Client disconnected. Connection handled gracefully.")
        except Exception as e:
            # This handler catches connection/parsing errors. Workflow errors are handled above.
            logger.error(f"An error occurred in WebSocket connection handler: {e}", exc_info=True)
            await self._render_error(str(e))


    async def _render_user_message(self, message: str, turn_id: str):
        template = templates.get_template("chat/partials/user_message.html").render(
            {"content": message, "turn_id": turn_id}
        )
        await self.ws_manager.send_html(template)

    async def _render_ai_bubble_placeholder(self, turn_id: str):
        template = templates.get_template("chat/partials/ai_message_placeholder.html").render(
            {"turn_id": turn_id}
        )
        await self.ws_manager.send_html(template)

    async def _render_ai_message_chunk(self, event: AIMessageChunkEvent, turn_id: str):
        context = {"delta": event.delta, "turn_id": turn_id}
        template = templates.get_template("chat/partials/ai_message_chunk.html").render(context)
        await self.ws_manager.send_html(template)

    async def _render_ai_message_controls(self, event: AIMessageCompletedEvent, turn_id: str):
        context = {"message": event.message, "turn_id": turn_id}
        template = templates.get_template("chat/partials/ai_message_controls.html").render(context)
        await self.ws_manager.send_html(template)

    async def _render_usage_metrics(self, event: UsageMetricsUpdatedEvent, turn_id: str):
        context = {
            "total_cost": event.total_cost,
            "input_tokens": event.input_tokens,
            "output_tokens": event.output_tokens,
        }
        template = templates.get_template("usage/partials/session_metrics.html").render(context)
        await self.ws_manager.send_html(template)

    async def _render_error(self, error_message: str):
        context = {"message": error_message}
        template = templates.get_template("components/actions/trigger_toast.html").render(context)
        await self.ws_manager.send_html(template)

    async def _handle_workflow_log(self, event: WorkflowLogEvent, **kwargs):
        color_map = {"info": "gray", "error": "red"}
        color = color_map.get(event.level, "gray")

        timestamp = datetime.now().strftime("%H:%M:%S")
        context = {"message": event.message, "color": color, "timestamp": timestamp}
        template = templates.get_template("logs/partials/log_item.html").render(context)
        await self.ws_manager.send_html(template)

    async def _render_workflow_error(self, event: WorkflowErrorEvent, turn_id: str):
        # Log the error to the logs panel
        await self._handle_workflow_log(WorkflowLogEvent(message=event.message, level=LogLevel.ERROR))

        # Remove AI message placeholder
        remove_template = templates.get_template("chat/partials/remove_ai_message.html").render(
            {"turn_id": turn_id}
        )
        await self.ws_manager.send_html(remove_template)

        # Render retry button on user message
        retry_template = templates.get_template("chat/partials/retry_button.html").render(
            {"turn_id": turn_id, "original_message": event.original_message}
        )
        await self.ws_manager.send_html(retry_template)

    async def _remove_user_message_controls(self, turn_id: str):
        template = templates.get_template("chat/partials/clear_user_message_controls.html").render(
            {"turn_id": turn_id}
        )
        await self.ws_manager.send_html(template)