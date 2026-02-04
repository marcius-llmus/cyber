import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

from fastapi import WebSocketDisconnect
from pydantic import ValidationError

from app.chat.schemas import Turn
from app.coder.schemas import (
    AgentStateEvent,
    AIMessageBlockStartEvent,
    AIMessageChunkEvent,
    CoderEvent,
    ContextFilesUpdatedEvent,
    LogLevel,
    SingleShotDiffAppliedEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    UsageMetricsUpdatedEvent,
    WebSocketMessage,
    WorkflowErrorEvent,
    WorkflowLogEvent,
)
from app.coder.services import CoderService, TurnExecution
from app.commons.websockets import WebSocketConnectionManager
from app.core.templating import templates
from app.patches.schemas.commons import PatchRepresentation

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
            AIMessageBlockStartEvent: self._render_text_block_start,
            AIMessageChunkEvent: self._render_ai_message_chunk,
            AgentStateEvent: self._render_agent_state,
            WorkflowErrorEvent: self._render_workflow_error,
            UsageMetricsUpdatedEvent: self._render_usage_metrics,
            WorkflowLogEvent: self._handle_workflow_log,
            ToolCallEvent: self._render_tool_call,
            ToolCallResultEvent: self._render_tool_result,
            SingleShotDiffAppliedEvent: self._render_single_shot_applied,
            ContextFilesUpdatedEvent: self._render_context_files_updated,
        }

    async def _process_event(self, event: CoderEvent, turn: Turn):
        # todo check later if it is okay to get by klass type directly
        if not (handler := self.event_handlers.get(type(event))):
            logger.warning(f"No handler for event type: {type(event)}")
            return
        await handler(event, turn=turn)

    async def _prepare_ui_for_new_turn(self, message_content: str, turn: Turn) -> str:
        await self._render_user_message(message_content, turn.turn_id)
        await self._render_ai_bubble_placeholder(turn.turn_id)
        await self._render_composer_running(turn.turn_id)
        return turn.turn_id

    async def _prepare_ui_for_retry_turn(self, turn: Turn) -> str:
        await self._render_ai_bubble_placeholder(turn.turn_id)
        await self._remove_user_message_controls(turn.turn_id)
        await self._render_composer_running(turn.turn_id)
        return turn.turn_id

    async def handle_connection(self):
        logger.info("WebSocket connection established.")
        execution = None

        try:
            while True:
                execution = None
                data = await self.ws_manager.receive_json()
                logger.info("Received JSON data from client.")

                try:
                    message = WebSocketMessage(**data)
                except ValidationError as e:
                    logger.error(f"WebSocket validation error: {e}", exc_info=True)
                    await self._render_error(f"Invalid message format: {e}")
                    continue

                execution = await self.coder_service.handle_user_message(
                    user_message=message.message,
                    session_id=self.session_id,
                    retry_turn_id=message.retry_turn_id,
                )

                if message.retry_turn_id:
                    await self._prepare_ui_for_retry_turn(execution.turn)
                else:
                    await self._prepare_ui_for_new_turn(
                        message.message, execution.turn
                    )

                try:
                    async for event in execution.stream:
                        await self._process_event(event, execution.turn)
                    
                    await self._render_composer_idle()

                except WebSocketDisconnect:
                    logger.info("Client disconnected during turn stream.")
                    await self._cancel_active_run(execution)
                    return

                # cancelled by user, we ignore as it was already cancelled
                # CancelledError means that by some other reason, it was cancelled already
                # so we don't really need to call handler.cancel() again
                except asyncio.CancelledError:
                    logger.info("Turn cancelled.")
                    return

                except Exception as e:
                    logger.error(
                        f"An error occurred in WebSocket turn {execution.turn.turn_id}: {e}",
                        exc_info=True,
                    )
                    await self._cancel_active_run(execution)
                    await self._render_workflow_error(
                        event=WorkflowErrorEvent(
                            message=str(e), original_message=message.message
                        ),
                        turn=execution.turn,
                    )
                    await self._render_composer_idle()

        except WebSocketDisconnect:
            logger.info("Client disconnected. Connection handled gracefully.")
            await self._cancel_active_run(execution)
            return

        except Exception as e:
            # This handler catches connection/parsing errors. Workflow errors are handled above.
            logger.error(
                f"An error occurred in WebSocket connection handler: {e}", exc_info=True
            )
            await self._cancel_active_run(execution)
            # todo: this crap is not working and I am too lazy to fix it now
            #       errors from inner agents works. this should not be happening at all, so we can see it later
            await self._render_error(str(e))

    @staticmethod
    async def _cancel_active_run(execution: TurnExecution | None) -> None:
        if not execution:
            return

        await execution.cancel()

    async def _render_user_message(self, message: str, turn_id: str):
        template = templates.get_template("chat/partials/user_message.html").render(
            {"content": message, "turn_id": turn_id}
        )
        await self.ws_manager.send_html(template)

    # todo: some receive turn, others turn id? what is the logic? let's make a pattern
    async def _render_ai_bubble_placeholder(self, turn_id: str):
        template = templates.get_template(
            "chat/partials/ai_message_placeholder.html"
        ).render({"turn_id": turn_id})
        await self.ws_manager.send_html(template)

    async def _render_text_block_start(
        self, event: AIMessageBlockStartEvent, turn: Turn, **kwargs
    ):
        """
        Mounts a new text block container when explicitly instructed by the service.
        """
        await self._mount_text_block_container(turn.turn_id, event.block_id)

    async def _render_ai_message_chunk(
        self, event: AIMessageChunkEvent, turn: Turn, **kwargs
    ):  # noqa
        context = {"delta": event.delta, "block_id": event.block_id}
        template = templates.get_template("chat/partials/ai_message_chunk.html").render(
            context
        )
        await self.ws_manager.send_html(template)

    async def _mount_text_block_container(self, turn_id: str, block_id: str):
        template = templates.get_template("chat/partials/markdown_block.html").render(
            {"turn_id": turn_id, "block_id": block_id}
        )
        await self.ws_manager.send_html(template)

    async def _render_agent_state(self, event: AgentStateEvent, turn: Turn, **kwargs):
        # Update status in UI
        context = {"status": event.status, "turn_id": turn.turn_id}
        template = templates.get_template("chat/partials/ai_status_update.html").render(
            context
        )
        await self.ws_manager.send_html(template)

        # Also log if status is not empty
        if event.status:
            await self._handle_workflow_log(
                WorkflowLogEvent(message=event.status, level=LogLevel.INFO)
            )

    async def _render_usage_metrics(
        self, event: UsageMetricsUpdatedEvent, turn: Turn, **kwargs
    ):  # noqa
        context = {
            "session_cost": event.session_cost,
            "monthly_cost": event.monthly_cost,
            "input_tokens": event.input_tokens,
            "output_tokens": event.output_tokens,
            "cached_tokens": event.cached_tokens,
        }
        template = templates.get_template(
            "usage/partials/session_metrics_oob.html"
        ).render({"metrics": context})
        await self.ws_manager.send_html(template)

    async def _render_tool_call(self, event: ToolCallEvent, turn: Turn, **kwargs):
        # ALWAYS Render the Tool Call Log Item (Footer)
        tool_context = {
            "tool_id": event.tool_id,
            "tool_name": event.tool_name,
            "tool_kwargs": event.tool_kwargs,
            "turn_id": turn.turn_id,
            "internal_tool_call_id": event.internal_tool_call_id,
        }
        html_response = templates.get_template(
            "chat/partials/tool_call_item_oob.html"
        ).render(tool_context)
        await self.ws_manager.send_html(html_response)

        # if it is apply_patch, ADDITIONALLY render the Visual Diff Card (Inline Stream)
        # todo: in coder service, check for tool call event type and create diff row from there
        if event.tool_name == "apply_patch":
            patch_text = event.tool_kwargs.get("patch", "")

            try:
                representation = PatchRepresentation.from_text(
                    raw_text=patch_text,
                    processor_type=turn.settings_snapshot.diff_patch_processor_type,
                )

                for parsed in representation.patches:
                    diff_context = {
                        "tool_id": event.tool_id,
                        "file_path": parsed.path,
                        "diff": parsed.diff,
                        "turn_id": turn.turn_id,
                        "additions": parsed.additions,
                        "deletions": parsed.deletions,
                        "internal_tool_call_id": event.internal_tool_call_id,
                        "tool_output": None,
                    }
                    diff_template = templates.get_template(
                        "patches/partials/diff_patch_item_oob.html"
                    ).render(diff_context)

                    await self.ws_manager.send_html(diff_template)
            except Exception as e:
                logger.warning(f"Failed to parse patch for presentation: {e}")
                await self._handle_workflow_log(
                    WorkflowLogEvent(
                        message=f"Error parsing patch for display: {e}",
                        level=LogLevel.ERROR,
                    )
                )

    async def _render_tool_result(
        self, event: ToolCallResultEvent, turn: Turn, **kwargs
    ):  # noqa
        await self._handle_workflow_log(
            WorkflowLogEvent(
                message=f"Tool `{event.tool_name}` finished.", level=LogLevel.INFO
            )
        )

        list_context = {
            "tool_id": event.tool_id,
            "tool_name": event.tool_name,
            "tool_output": event.tool_output,
            "internal_tool_call_id": event.internal_tool_call_id,
        }
        html_response = templates.get_template(
            "chat/partials/tool_call_result.html"
        ).render(list_context)
        await self.ws_manager.send_html(html_response)

        # if it's a Diff Patch, ALSO update the Inline Visual Card
        if event.tool_name == "apply_patch":
            diff_context = {
                "tool_id": event.tool_id,
                "internal_tool_call_id": event.internal_tool_call_id,
            }
            diff_template = templates.get_template(
                "patches/partials/diff_patch_result.html"
            ).render(diff_context)
            await self.ws_manager.send_html(diff_template)

    async def _render_single_shot_applied(
        self, event: SingleShotDiffAppliedEvent, turn: Turn, **kwargs
    ):
        await self._handle_workflow_log(
            WorkflowLogEvent(
                message=f"Single-shot patch applied to {event.file_path}: {event.output}",
                level=LogLevel.INFO,
            )
        )

    async def _render_composer_running(self, turn_id: str):
        template = templates.get_template("chat/partials/message_form_running.html").render(
            {"turn_id": turn_id}
        )
        await self.ws_manager.send_html(template)

    async def _render_composer_idle(self, content: str = ""):
        context = {"content": content}
        template = templates.get_template("chat/partials/message_form.html").render(context)
        await self.ws_manager.send_html(template)

    async def _render_context_files_updated(
        self, event: ContextFilesUpdatedEvent, turn: Turn, **kwargs
    ):  # noqa
        template = templates.get_template(
            "context/partials/context_file_list_items.html"
        ).render({"files": event.files, "session_id": event.session_id})
        await self.ws_manager.send_html(template)

    async def _render_error(self, error_message: str):
        context = {"message": error_message}
        template = templates.get_template(
            "components/actions/trigger_toast.html"
        ).render(context)
        await self.ws_manager.send_html(template)

    async def _handle_workflow_log(self, event: WorkflowLogEvent, **kwargs):  # noqa
        color_map = {"info": "gray", "error": "red"}
        color = color_map.get(event.level, "gray")

        timestamp = datetime.now().strftime("%H:%M:%S")
        context = {"message": event.message, "color": color, "timestamp": timestamp}
        template = templates.get_template("logs/partials/log_item.html").render(context)
        await self.ws_manager.send_html(template)

    async def _render_workflow_error(
        self, event: WorkflowErrorEvent, turn: Turn, **kwargs
    ):
        # Log the error to the logs panel
        await self._handle_workflow_log(
            WorkflowLogEvent(message=event.message, level=LogLevel.ERROR)
        )

        # Remove AI message placeholder
        remove_template = templates.get_template(
            "chat/partials/remove_ai_message.html"
        ).render({"turn_id": turn.turn_id})
        await self.ws_manager.send_html(remove_template)

        # Render retry button on user message
        retry_template = templates.get_template(
            "chat/partials/retry_button.html"
        ).render({"turn_id": turn.turn_id, "original_message": event.original_message})
        await self.ws_manager.send_html(retry_template)

    async def _remove_user_message_controls(self, turn_id: str):
        template = templates.get_template(
            "chat/partials/clear_user_message_controls.html"
        ).render({"turn_id": turn_id})
        await self.ws_manager.send_html(template)
