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

from app.core.db import DatabaseSessionManager
from app.chat.services import ChatService
from app.coder.schemas import (
    AIMessageChunkEvent,
    AIMessageCompletedEvent,
    CoderEvent,
    WorkflowErrorEvent,
    WorkflowLogEvent,
    LogLevel,
    UsageMetricsUpdatedEvent,
)
from app.context.services import WorkspaceService
from app.agents.services import WorkflowService
from app.history.enums import HistoryEventType
from app.usage.services import UsagePageService
from app.usage.schemas import SessionMetrics
from app.prompts.enums import PromptEventType
from app.projects.exceptions import ActiveProjectRequiredException
from app.history.exceptions import ChatSessionNotFoundException


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
        try:
            async with self.db.session() as session:
                workflow = await self.agent_factory(session, session_id)

                workflow_service = await self.workflow_service_factory(session)
                
                ctx = await workflow_service.get_context(session_id, workflow)

                chat_service = await self.chat_service_factory(session)
                db_messages = await chat_service.get_messages_for_session(session_id=session_id)
                chat_history = [
                    ChatMessage(role=msg.role, content=msg.content) for msg in db_messages
                ]

            handler = workflow.run(
                user_msg=user_message, chat_history=chat_history, ctx=ctx
            )

            async for event in handler.stream_events():
                if coder_event := await self._process_workflow_event(event):
                    yield coder_event
                else:
                    logger.debug(f"Skipped processing for event type: {type(event)}")

            logger.info(f"Workflow stream finished for session {session_id}.")

            # Await the handler to get the final result and ensure completion.
            llm_full_response = await handler
            final_content = str(llm_full_response)

            # session here is the db session
            # session_id is the 'history', the one user can delete, not db
            async with self.db.session() as session:
                chat_service = await self.chat_service_factory(session)
                await chat_service.add_user_message(session_id=session_id, content=user_message)
                await chat_service.add_ai_message(session_id=session_id, content=final_content)

                # Persist Context State
                workflow_service = await self.workflow_service_factory(session)
                await workflow_service.save_context(session_id, ctx)

                # Process Usage and get Event
                usage_service = await self.usage_service_factory(session)
                metrics = await usage_service.process_workflow_usage(session_id, llm_full_response)

            # Emit Usage Event
            yield UsageMetricsUpdatedEvent(
                session_cost=metrics.session_cost,
                monthly_cost=metrics.monthly_cost,
                input_tokens=metrics.input_tokens,
                output_tokens=metrics.output_tokens,
                cached_tokens=metrics.cached_tokens
            )

            yield AIMessageCompletedEvent(
                message=final_content
            )
        except Exception as e:
            yield await self._handle_workflow_exception(e, original_message=user_message)

    async def _process_workflow_event(self, event: Event) -> CoderEvent | None:
        logger.debug(f"Processing workflow event: {type(event)}")
        
        if isinstance(event, AgentStream):
            return await self._handle_agent_stream(event)
        elif isinstance(event, ToolCall):
            return await self._handle_tool_call(event)
        elif isinstance(event, ToolCallResult):
            return await self._handle_tool_call_result(event)
        elif isinstance(event, AgentInput):
            return await self._handle_agent_input(event)
        elif isinstance(event, AgentOutput):
            return await self._handle_agent_output(event)
        elif isinstance(event, StopEvent):
            return None

        logger.warning(f"Unknown event type from workflow: {type(event)}")
        return None

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
    async def _handle_agent_stream(event: AgentStream) -> AIMessageChunkEvent | None:
        logger.debug(f"Handling AgentStream. Delta: '{event.delta}'")
        if event.delta:
            return AIMessageChunkEvent(delta=event.delta)
        else:
            logger.debug("AgentStream event received but delta was empty.")
        return None

    @staticmethod
    async def _handle_agent_input(event: AgentInput) -> WorkflowLogEvent: # noqa
        return WorkflowLogEvent(message="Agent is planning next steps...", level=LogLevel.INFO)

    @staticmethod
    async def _handle_agent_output(event: AgentOutput) -> WorkflowLogEvent:
        content = ""
        if event.response and event.response.content:
            content = f" Output: {event.response.content[:50]}..."
        return WorkflowLogEvent(message=f"Agent step completed.{content}", level=LogLevel.INFO)

    @staticmethod
    async def _handle_tool_call(event: ToolCall) -> WorkflowLogEvent:
        message = f"Calling tool `{event.tool_name}` with arguments: {event.tool_kwargs}"
        return WorkflowLogEvent(message=f"Workflow Log: {message}", level=LogLevel.INFO)

    @staticmethod
    async def _handle_tool_call_result(
        event: ToolCallResult,
    ) -> WorkflowLogEvent:
        message = f"Tool `{event.tool_name}` returned: {event.tool_output.content}"
        return WorkflowLogEvent(
            message=f"Workflow Log: {message}", level=LogLevel.INFO
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
