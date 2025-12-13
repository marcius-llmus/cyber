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
    AgentStateEvent,
    UsageMetricsUpdatedEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    WebSocketMessage,
    WorkflowErrorEvent,
    WorkflowLogEvent,
    LogLevel
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
        self.active_text_block_id: str | None = None
        self.event_handlers: dict[type, Handler] = {
            AIMessageChunkEvent: self._render_ai_message_chunk,
            AIMessageCompletedEvent: self._render_ai_message_controls,
            AgentStateEvent: self._render_agent_state,
            WorkflowErrorEvent: self._render_workflow_error,
            UsageMetricsUpdatedEvent: self._render_usage_metrics,
            WorkflowLogEvent: self._handle_workflow_log,
            ToolCallEvent: self._render_tool_call,
            ToolCallResultEvent: self._render_tool_result,
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
        self.active_text_block_id = None
        await self._render_user_message(message_content, turn_id)
        await self._render_ai_bubble_placeholder(turn_id)
        await self._ensure_active_text_block(turn_id)
        return turn_id

    async def _prepare_ui_for_retry_turn(self, turn_id: str) -> str:
        self.active_text_block_id = None
        await self._render_ai_bubble_placeholder(turn_id)
        await self._ensure_active_text_block(turn_id)
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

    async def _ensure_active_text_block(self, turn_id: str):
        """
        Ensures there is an active text container in the DOM to receive streaming chunks.
        If the stream was interrupted (e.g. by a Tool or at start), this mounts a new container.
        """
        if not self.active_text_block_id:
            self.active_text_block_id = str(uuid.uuid4())
            await self._mount_text_block_container(turn_id, self.active_text_block_id)

    def _close_active_text_block(self):
        """
        Marks the current text block as finished.
        The next text chunk will be forced to mount a new container
        within the current turn's stream (same turn_id).
        """
        self.active_text_block_id = None

    async def _render_ai_message_chunk(self, event: AIMessageChunkEvent, turn_id: str):
        await self._ensure_active_text_block(turn_id)

        context = {"delta": event.delta, "block_id": self.active_text_block_id}
        template = templates.get_template("chat/partials/ai_message_chunk.html").render(context)
        await self.ws_manager.send_html(template)

    async def _mount_text_block_container(self, turn_id: str, block_id: str):
        template = templates.get_template("chat/partials/markdown_block.html").render(
            {"turn_id": turn_id, "block_id": block_id}
        )
        await self.ws_manager.send_html(template)

    async def _render_ai_message_controls(self, event: AIMessageCompletedEvent, turn_id: str):
        context = {"message": event.message, "turn_id": turn_id}
        template = templates.get_template("chat/partials/ai_message_controls.html").render(context)
        await self.ws_manager.send_html(template)
        await self._render_agent_state(AgentStateEvent(status=""), turn_id)

    async def _render_agent_state(self, event: AgentStateEvent, turn_id: str):
        # Update status in UI
        context = {"status": event.status, "turn_id": turn_id}
        template = templates.get_template("chat/partials/ai_status_update.html").render(context)
        await self.ws_manager.send_html(template)
        
        # Also log if status is not empty
        if event.status:
            await self._handle_workflow_log(WorkflowLogEvent(message=event.status, level=LogLevel.INFO))
        
    async def _render_usage_metrics(self, event: UsageMetricsUpdatedEvent, turn_id: str): # noqa
        context = {
            "session_cost": event.session_cost,
            "monthly_cost": event.monthly_cost,
            "input_tokens": event.input_tokens,
            "output_tokens": event.output_tokens,
            "cached_tokens": event.cached_tokens,
        }
        template = templates.get_template("usage/partials/session_metrics.html").render(
            {"metrics": context, "use_oob": True}
        )
        await self.ws_manager.send_html(template)

    async def _render_tool_call(self, event: ToolCallEvent, turn_id: str):
        # 1. ALWAYS Render the Tool Call Log Item (Footer)
        tool_context = {
            "tool_id": event.tool_id,
            "tool_name": event.tool_name,
            "tool_kwargs": event.tool_kwargs,
            "turn_id": turn_id,
            "tool_run_id": event.tool_run_id,
        }
        html_response = templates.get_template("chat/partials/tool_call_item.html").render(tool_context)
        await self.ws_manager.send_html(html_response)

        # 2. If it is apply_diff, ADDITIONALLY render the Visual Diff Card (Inline Stream)
        if event.tool_name == "apply_diff":
            file_path = event.tool_kwargs.get("file_path", "unknown")
            diff = event.tool_kwargs.get("diff", "")
            
            # Calculate stats
            lines = diff.splitlines()
            additions = sum(1 for line in lines if line.startswith('+') and not line.startswith('+++'))
            deletions = sum(1 for line in lines if line.startswith('-') and not line.startswith('---'))
            
            diff_context = {
                "tool_id": event.tool_id,
                "file_path": file_path,
                "diff": diff,
                "turn_id": turn_id,
                "additions": additions,
                "deletions": deletions,
                "tool_run_id": event.tool_run_id,
            }
            diff_template = templates.get_template("chat/partials/diff_patch_item.html").render(diff_context)
            
            await self.ws_manager.send_html(diff_template)

            # Close the current text block so the next text chunk starts a new one AFTER this diff
            self._close_active_text_block()

    async def _render_tool_result(self, event: ToolCallResultEvent, turn_id: str): # noqa
        await self._handle_workflow_log(
             WorkflowLogEvent(message=f"Tool `{event.tool_name}` finished.", level=LogLevel.INFO)
        )

        list_context = {
            "tool_id": event.tool_id,
            "tool_name": event.tool_name,
            "tool_output": event.tool_output,
            "tool_run_id": event.tool_run_id,
        }
        html_response = templates.get_template("chat/partials/tool_call_result.html").render(list_context)
        await self.ws_manager.send_html(html_response)

        # 2. If it's a Diff Patch, ALSO update the Inline Visual Card
        if event.tool_name == "apply_diff":
            diff_context = {"tool_id": event.tool_id, "tool_run_id": event.tool_run_id}
            diff_template = templates.get_template("chat/partials/diff_patch_result.html").render(diff_context)
            await self.ws_manager.send_html(diff_template)

    async def _render_error(self, error_message: str):
        context = {"message": error_message}
        template = templates.get_template("components/actions/trigger_toast.html").render(context)
        await self.ws_manager.send_html(template)

    async def _handle_workflow_log(self, event: WorkflowLogEvent, **kwargs): # noqa
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