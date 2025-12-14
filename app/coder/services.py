import logging
from asyncio import Event
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
from llama_index.core.workflow import StopEvent

from app.core.config import settings
from app.usage.exceptions import UsageTrackingException
from app.core.db import DatabaseSessionManager
from app.chat.services import ChatService
from app.coder.schemas import (
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
from app.usage.schemas import SessionMetrics
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
        self.db = db
        self.chat_service_factory = chat_service_factory
        self.agent_factory = agent_factory
        self.workflow_service_factory = workflow_service_factory
        self.usage_service_factory = usage_service_factory

    async def handle_user_message(
        self, *, user_message: str, session_id: int
    ) -> AsyncGenerator[CoderEvent, None]:
        yield AgentStateEvent(status="Thinking...")

        async with UsageCollector() as event_collector:
            async with self.db.session() as session:
                workflow = await self.agent_factory(session, session_id)

                workflow_service = await self.workflow_service_factory(session)
                
                ctx = await workflow_service.get_context(session_id, workflow)

                chat_service = await self.chat_service_factory(session)
                db_messages = await chat_service.get_messages_for_session(session_id=session_id)
                chat_history = [
                    ChatMessage(role=msg.role, content=msg.content) for msg in db_messages
                ]
                
                # Track how many events we have already processed to avoid double-counting
                processed_events_count = 0

            try:
                handler = workflow.run(
                    user_msg=user_message, chat_history=chat_history, ctx=ctx, max_iterations=settings.AGENT_MAX_ITERATIONS
                )

                async for event in handler.stream_events():
                    async for coder_event in self._process_workflow_event(event):
                        yield coder_event
                    
                    new_events, processed_events_count = self._slice_new_events(event_collector, processed_events_count)
                    async for usage_event in self._track_and_yield_usage(session_id, new_events):
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
                        tool_calls=None,
                        diff_patches=None
                    )

                    # Persist Context State
                    workflow_service = await self.workflow_service_factory(session)
                    await workflow_service.save_context(session_id, ctx)

                    # Process any REMAINING usage events (e.g. from the final response generation)
                    # The loop might finish before the final events are caught if they happen in the final return
                    new_events, processed_events_count = self._slice_new_events(event_collector, processed_events_count)
                    async for usage_event in self._track_and_yield_usage(session_id, new_events):
                        yield usage_event

                yield AIMessageCompletedEvent(
                    message=final_content
                )
            except Exception as e:
                yield await self._handle_workflow_exception(e, original_message=user_message)
            finally:
                # Safety check: Log if any events were left behind (e.g., due to a crash before final save)
                unprocessed_count = len(event_collector) - processed_events_count
                if unprocessed_count > 0:
                    logger.warning(f"Session {session_id}: {unprocessed_count} usage events were not processed/persisted.")

    @staticmethod
    def _slice_new_events(collector: list, processed_count: int) -> tuple[list, int]:
        current_count = len(collector)
        if current_count > processed_count:
            return collector[processed_count:], current_count
        return [], processed_count

    async def _track_and_yield_usage(self, session_id: int, events: list) -> AsyncGenerator[CoderEvent, None]:
        """Helper to process a batch of usage events and yield updates/errors."""

        async with self.db.session() as session:
            usage_service = await self.usage_service_factory(session)
            for event in events:
                try:
                    await usage_service.track_event(session_id, event)
                except UsageTrackingException as e:
                    yield WorkflowLogEvent(message=str(e), level=LogLevel.ERROR)
            
            metrics = await usage_service.get_session_metrics(session_id)

        yield UsageMetricsUpdatedEvent(
            session_cost=metrics.session_cost,
            monthly_cost=metrics.monthly_cost,
            input_tokens=metrics.input_tokens,
            output_tokens=metrics.output_tokens,
            cached_tokens=metrics.cached_tokens
        )

    async def _process_workflow_event(self, event: Event) -> AsyncGenerator[CoderEvent, None]:
        logger.debug(f"Processing workflow event: {type(event)}")
        
        if isinstance(event, AgentStream):
            async for e in self._handle_agent_stream(event):
                yield e
        elif isinstance(event, ToolCall):
            yield AgentStateEvent(status=f"Calling tool `{event.tool_name}`...")
            yield await self._handle_tool_call(event)
        elif isinstance(event, ToolCallResult):
            yield await self._handle_tool_call_result(event)
        elif isinstance(event, AgentInput):
            async for e in self._handle_agent_input(event):
                yield e
        elif isinstance(event, AgentOutput):
            async for e in self._handle_agent_output(event):
                yield e
        elif isinstance(event, StopEvent):
            pass
        else:
            logger.warning(f"Unknown event type from workflow: {type(event)}")

    @staticmethod
    async def _handle_workflow_exception(e: Exception, original_message: str) -> WorkflowErrorEvent:
        error_message = str(e)
        logger.error(f"Workflow execution failed: {error_message}", exc_info=True)
        # The log event is removed to conform to the single-return contract.
        return WorkflowErrorEvent(
            message=f"Workflow Error: {error_message}",
            original_message=original_message,
        )

    @staticmethod
    async def _handle_agent_stream(event: AgentStream) -> AsyncGenerator[CoderEvent, None]:
        if event.delta:
            yield AIMessageChunkEvent(delta=event.delta)
        
        # Handle tool call construction (if streaming)
        if event.tool_calls:
             yield AgentStateEvent(status=f"Calling {len(event.tool_calls)} tools...")

    @staticmethod
    async def _handle_agent_input(event: AgentInput) -> AsyncGenerator[CoderEvent, None]: # noqa
        # Yield a state event to show "Thinking..." in the UI
        yield AgentStateEvent(status="Agent is planning next steps...")

    @staticmethod
    async def _handle_agent_output(event: AgentOutput) -> AsyncGenerator[CoderEvent, None]:
        content = ""
        if event.response and event.response.content:
            content = f" Output: {event.response.content[:50]}..."
        
        yield WorkflowLogEvent(message=f"Agent step completed.{content}", level=LogLevel.INFO)
        # Clear the status
        yield AgentStateEvent(status="")

    @staticmethod
    def _get_run_id(tool_kwargs: dict[str, Any], tool_name: str) -> str:
        if not (unique_id := tool_kwargs.get("_run_id")):
            raise ValueError(f"Run ID not found for tool {tool_name}")
        return unique_id

    async def _handle_tool_call(self, event: ToolCall) -> ToolCallEvent:
        unique_id = self._get_run_id(event.tool_kwargs, event.tool_name)
        return ToolCallEvent(
            tool_name=event.tool_name,
            tool_kwargs=event.tool_kwargs,
            tool_id=event.tool_id,
            tool_run_id=unique_id,
        )

    async def _handle_tool_call_result(
        self,
        event: ToolCallResult,
    ) -> ToolCallResultEvent:
        content = str(event.tool_output.content) if event.tool_output else ""
        unique_id = self._get_run_id(event.tool_kwargs, event.tool_name)

        return ToolCallResultEvent(
            tool_name=event.tool_name,
            tool_output=content,
            tool_id=event.tool_id,
            tool_run_id=unique_id,
        )


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
        return {
            "metrics": SessionMetrics(
                session_cost=0,
                monthly_cost=0,
                input_tokens=0,
                output_tokens=0,
                cached_tokens=0,
            ),
            "session": None,
            "messages": [],
            "files": [],
            "active_project": active_project,
        }
