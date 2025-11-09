import logging
from asyncio import Event
from typing import AsyncGenerator

from llama_index.core.agent import AgentStream, ToolCall, ToolCallResult
from llama_index.core.llms import ChatMessage
from workflows import Context

from app.chat.services import ChatService
from app.coder.schemas import (
    AIMessageChunkEvent,
    AIMessageCompletedEvent,
    CoderEvent,
    WorkflowErrorEvent,
    WorkflowLogEvent,
    LogLevel,
)
from app.usage.services import UsageService, UsagePageService
from app.workflows.factory import WorkflowFactory


logger = logging.getLogger(__name__)


class CoderService:
    def __init__(
        self,
        chat_service: ChatService,
        usage_service: UsageService,
        workflow_factory: WorkflowFactory,
    ):
        self.chat_service = chat_service
        self.usage_service = usage_service
        self.workflow_factory = workflow_factory

    async def _get_workflow_handler(self, user_message: str, session_id: int):
        # TODO: Tools should be dynamic, that's why we use factory: a new workflow for every message
        workflow = await self.workflow_factory.create_function_agent(tools=[])
        chat_history = await self._build_chat_history(session_id=session_id)
        ctx = Context(workflow)

        handler = workflow.run(
            input=user_message, chat_history=chat_history, ctx=ctx
        )
        return handler

    async def handle_user_message(
        self, *, user_message: str, session_id: int
    ) -> AsyncGenerator[CoderEvent, None]:
        try:
            self.chat_service.add_user_message(session_id=session_id, content=user_message)

            handler = await self._get_workflow_handler(user_message, session_id)

            async for event in handler.stream_events():
                if coder_event := await self._process_workflow_event(event):
                    yield coder_event

            # Await the handler to get the final result and ensure completion.
            llm_full_response = await handler
            self.chat_service.add_ai_message(session_id=session_id, content=str(llm_full_response))

            yield AIMessageCompletedEvent(
                message=str(llm_full_response)
            )
        except Exception as e:
            yield await self._handle_workflow_exception(e, original_message=user_message)

    async def _process_workflow_event(self, event: Event) -> CoderEvent | None:
        if isinstance(event, AgentStream):
            return await self._handle_agent_stream(event)
        elif isinstance(event, ToolCall):
            return await self._handle_tool_call(event)
        elif isinstance(event, ToolCallResult):
            return await self._handle_tool_call_result(event)

        logger.warning(f"Unknown event type from workflow: {type(event)}")
        return None

    async def _build_chat_history(self, session_id: int) -> list[ChatMessage]:
        db_messages = self.chat_service.get_messages_for_session(session_id=session_id)

        chat_history = [
            ChatMessage(role=msg.role, content=msg.content) for msg in db_messages
        ]
        return chat_history

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
        if event.delta:
            return AIMessageChunkEvent(delta=event.delta)
        return None

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

    def __init__(self, usage_page_service: UsagePageService, chat_service: ChatService):
        self.usage_page_service = usage_page_service
        self.chat_service = chat_service

    def get_main_page_data(self, session_id: int) -> dict:
        """Aggregates data from various services for the main page view."""
        usage_data = self.usage_page_service.get_session_metrics_page_data()
        session = self.chat_service.get_session_by_id(session_id=session_id)
        return {
            **usage_data,
            "session": session,
            "messages": session.messages,
        }
