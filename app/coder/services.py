import logging
import uuid
from typing import Any, AsyncGenerator, Callable, Coroutine, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession
from llama_index.core.agent.workflow.workflow_events import (
    AgentInput,
    AgentOutput,
    AgentStream,
    ToolCall,
    ToolCallResult,
)
from llama_index.core.llms import ChatMessage
from app.core.config import settings
from app.core.db import DatabaseSessionManager
from app.chat.services import ChatService
from app.coder.schemas import (
    AIMessageBlockStartEvent,
    AIMessageChunkEvent,
    AIMessageCompletedEvent,
    CoderEvent,
    WorkflowErrorEvent,
    WorkflowLogEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    LogLevel,
    UsageMetricsUpdatedEvent,
    AgentStateEvent,
)
from app.context.services import WorkspaceService
from app.agents.services import WorkflowService
from app.history.enums import HistoryEventType
from app.usage.services import UsagePageService
from app.usage.event_handlers import UsageCollector
from app.prompts.enums import PromptEventType


logger = logging.getLogger(__name__)


class CoderService:
    def __init__(
        self,
        db: DatabaseSessionManager, # this is not a session, but the manager
        chat_service_factory: Callable[[AsyncSession], Awaitable[ChatService]],
        workflow_service_factory: Callable[[AsyncSession], Awaitable[WorkflowService]],
        agent_factory: Callable[[AsyncSession, int], Coroutine[Any, Any, Any]],
        usage_service_factory: Callable[[AsyncSession], Awaitable[Any]],
    ):
        self.tool_calls: dict[str, dict[str, Any]] = {}
        self.ordered_blocks: list[dict[str, Any]] = []
        self.current_text_block_id: str | None = None
        self.db = db
        self.chat_service_factory = chat_service_factory
        self.agent_factory = agent_factory
        self.workflow_service_factory = workflow_service_factory
        self.usage_service_factory = usage_service_factory
        self.handlers: dict[type, Callable[[Any], AsyncGenerator[CoderEvent, None]]] = {
            AgentStream: self._handle_agent_stream_event,
            ToolCall: self._handle_tool_call_event,
            ToolCallResult: self._handle_tool_call_result_event,
            AgentInput: self._handle_agent_input_event,
            AgentOutput: self._handle_agent_output_event,
        }

    async def handle_user_message(
        self, *, user_message: str, session_id: int
    ) -> AsyncGenerator[CoderEvent, None]:
        self.tool_calls = {}
        self.ordered_blocks = []
        self.current_text_block_id = None
        yield AgentStateEvent(status="Thinking...")

        async with UsageCollector() as event_collector:
            async with self.db.session() as session:
                workflow = await self.agent_factory(session, session_id)

                workflow_service = await self.workflow_service_factory(session)
                
                ctx = await workflow_service.get_context(session_id, workflow)

                chat_service = await self.chat_service_factory(session)
                db_messages = await chat_service.list_messages_by_session(session_id=session_id)
                chat_history = [
                    ChatMessage(role=msg.role, content=msg.content) for msg in db_messages
                ]

            try:
                handler = workflow.run(
                    user_msg=user_message, chat_history=chat_history, ctx=ctx, max_iterations=settings.AGENT_MAX_ITERATIONS
                )

                async for event in handler.stream_events():
                    async for coder_event in self._dispatch_event(event):
                        yield coder_event
                     
                    async for usage_event in self._process_new_usage(session_id, event_collector):
                        yield usage_event

                logger.info(f"Workflow stream finished for session {session_id}.")

                # Await the handler to get the final result and ensure completion.
                llm_full_response = await handler
                final_content = str(llm_full_response)

                # session here is the db session
                # session_id is the 'history', the one user can delete, not db
                async with self.db.session() as session:
                    chat_service = await self.chat_service_factory(session)
                    await chat_service.add_user_message(session_id=session_id, content=user_message)
                    await chat_service.add_ai_message(
                        session_id=session_id,
                        content=final_content,
                        tool_calls=list(self.tool_calls.values()),
                        blocks=self.ordered_blocks,
                    )

                    # Persist Context State
                    workflow_service = await self.workflow_service_factory(session)
                    await workflow_service.save_context(session_id, ctx)
                    
                    # Process remaining usage events
                    async for usage_event in self._process_new_usage(session_id, event_collector):
                        yield usage_event

                yield AIMessageCompletedEvent(
                    message=final_content
                )
            except Exception as e:
                yield await self._handle_workflow_exception(e, original_message=user_message)
            finally:
                # Safety check: Log if any events were left behind (e.g., due to a crash before final save)
                unprocessed_count = event_collector.unprocessed_count
                if unprocessed_count > 0:
                    logger.warning(f"Session {session_id}: {unprocessed_count} usage events were not processed/persisted.")

    async def _dispatch_event(self, event: Any) -> AsyncGenerator[CoderEvent, None]:
        if not (handler := self.handlers.get(type(event))):
            logger.warning(f"No handler for event type: {type(event)}")
            return

        async for coder_event in handler(event):
            yield coder_event

    async def _handle_agent_stream_event(self, event: AgentStream) -> AsyncGenerator[CoderEvent, None]:
        if event.delta:
            async for chunk_event in self._handle_agent_stream_delta(event):
                yield chunk_event
        if event.tool_calls:
            yield await self._handle_agent_stream_tool_calls(event)

    async def _handle_tool_call_event(self, event: ToolCall) -> AsyncGenerator[CoderEvent, None]:
        self.current_text_block_id = None
        yield await self._handle_tool_call_status(event)
        tool_event = await self._build_tool_call_event(event)
        self._record_tool_call(tool_event)
        yield tool_event

    # ToolCallResultEvent is our own event
    async def _handle_tool_call_result_event(self, event: ToolCallResult) -> AsyncGenerator[CoderEvent, None]:
        result_event = await self._build_tool_call_result_event(event)
        self._record_tool_result(result_event)
        yield result_event

    async def _handle_agent_input_event(self, event: AgentInput) -> AsyncGenerator[CoderEvent, None]:
        yield await self._handle_agent_input(event)

    async def _handle_agent_output_event(self, event: AgentOutput) -> AsyncGenerator[CoderEvent, None]:
        yield await self._handle_agent_output_log(event)
        yield await self._handle_agent_output_status(event)

    async def _process_new_usage(self, session_id: int, collector: UsageCollector) -> AsyncGenerator[CoderEvent, None]:
        """Helper to consume new events from collector and yield metrics updates."""
        new_events = collector.consume()
        if not new_events:
            return

        async with self.db.session() as session:
            usage_service = await self.usage_service_factory(session)
            metrics = await usage_service.process_batch(session_id, new_events)

        yield UsageMetricsUpdatedEvent(
            session_cost=metrics.session_cost,
            monthly_cost=metrics.monthly_cost,
            input_tokens=metrics.input_tokens,
            output_tokens=metrics.output_tokens,
            cached_tokens=metrics.cached_tokens
        )

    @staticmethod
    async def _handle_workflow_exception(e: Exception, original_message: str) -> WorkflowErrorEvent:
        error_message = str(e)
        logger.error(f"Workflow execution failed: {error_message}", exc_info=True)
        # The log event is removed to conform to the single-return contract.
        return WorkflowErrorEvent(
            message=f"Workflow Error: {error_message}",
            original_message=original_message,
        )

    async def _handle_agent_stream_delta(self, event: AgentStream) -> AsyncGenerator[CoderEvent, None]:
        if self.current_text_block_id is None:
            self.current_text_block_id = str(uuid.uuid4())
            
            # Start a new text block in our ordered history
            self.ordered_blocks.append({
                "type": "text",
                "block_id": self.current_text_block_id,
                "content": ""
            })
            
            yield AIMessageBlockStartEvent(block_id=self.current_text_block_id)

        # Append content to the current text block
        # (We assume the last block is the active one because ID matches)
        if self.ordered_blocks and self.ordered_blocks[-1].get("block_id") == self.current_text_block_id:
            self.ordered_blocks[-1]["content"] += event.delta

        yield AIMessageChunkEvent(delta=event.delta, block_id=self.current_text_block_id)

    @staticmethod
    async def _handle_agent_stream_tool_calls(event: AgentStream) -> AgentStateEvent:
        return AgentStateEvent(status=f"Calling {len(event.tool_calls)} tools...")

    @staticmethod
    async def _handle_tool_call_status(event: ToolCall) -> AgentStateEvent:
        return AgentStateEvent(status=f"Calling tool `{event.tool_name}`...")

    async def _build_tool_call_event(self, event: ToolCall) -> ToolCallEvent:
        unique_id = self._get_run_id(event.tool_kwargs, event.tool_name)
        return ToolCallEvent(
            tool_name=event.tool_name,
            tool_kwargs=event.tool_kwargs,
            tool_id=event.tool_id,
            tool_run_id=unique_id,
        )

    async def _build_tool_call_result_event(
        self,
        event: ToolCallResult,
    ) -> ToolCallResultEvent:
        content = str(event.tool_output.content)
        unique_id = self._get_run_id(event.tool_kwargs, event.tool_name)

        return ToolCallResultEvent(
            tool_name=event.tool_name,
            tool_output=content,
            tool_id=event.tool_id,
            tool_run_id=unique_id,
        )


    @staticmethod
    async def _handle_agent_input(event: AgentInput) -> AgentStateEvent: # noqa
        return AgentStateEvent(status="Agent is planning next steps...")

    @staticmethod
    async def _handle_agent_output_log(event: AgentOutput) -> WorkflowLogEvent:
        content = ""
        if event.response and event.response.content:
            content = f" Output: {event.response.content[:50]}..."
        return WorkflowLogEvent(message=f"Agent step completed.{content}", level=LogLevel.INFO)

    @staticmethod
    async def _handle_agent_output_status(event: AgentOutput) -> AgentStateEvent: # noqa
        return AgentStateEvent(status="")

    @staticmethod
    def _get_run_id(tool_kwargs: dict[str, Any], tool_name: str) -> str:
        if not (unique_id := tool_kwargs.get("_run_id")):
            raise ValueError(f"Run ID not found for tool {tool_name}")
        return unique_id

    def _record_tool_call(self, event: ToolCallEvent):
        self.tool_calls[event.tool_run_id] = {
            "id": event.tool_id,
            "name": event.tool_name,
            "kwargs": event.tool_kwargs,
            "run_id": event.tool_run_id,
            "output": None,
        }
        
        # Record the tool block in our ordered history
        self.ordered_blocks.append({
            "type": "tool",
            "tool_run_id": event.tool_run_id,
            "tool_name": event.tool_name,
        })

    def _record_tool_result(self, event: ToolCallResultEvent):
        if event.tool_run_id in self.tool_calls:
            self.tool_calls[event.tool_run_id]["output"] = event.tool_output
            return
        raise ValueError(f"Trying to record a tool result for a non existent tool call for event: {event}")


class CoderPageService:
    """
    This service is responsible for aggregating data for the main coder page.
    It orchestrates calls to other page services to build the complete context
    needed for rendering the initial HTML page.
    """

    def __init__(
        self,
        usage_page_service: UsagePageService,
        chat_service: ChatService,
        context_service: WorkspaceService,
    ):
        self.usage_page_service = usage_page_service
        self.chat_service = chat_service
        self.context_service = context_service

    async def get_main_page_data(self, session_id: int | None = None) -> dict:
        """Aggregates data from various services for the main page view."""
        if session_id and (session := await self.chat_service.get_session_by_id(session_id=session_id)):
            usage_data = await self.usage_page_service.get_session_metrics_page_data()
            context_files = await self.context_service.get_active_context(session.id)
            page_data = {
                **usage_data,
                "session": session,
                "messages": session.messages,
                "files": context_files,
                "active_project": session.project,
            }
        else:
            page_data = await self._get_empty_session_data()

        return {
            **page_data,
            "PromptEventType": PromptEventType,
            "HistoryEventType": HistoryEventType,
        }

    async def _get_empty_session_data(self) -> dict:
        active_project = await self.chat_service.project_service.get_active_project()
        usage_data = await self.usage_page_service.get_empty_metrics_page_data()
        return {
            **usage_data,
            "session": None,
            "messages": [],
            "files": [],
            "active_project": active_project,
        }