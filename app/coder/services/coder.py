import logging
from typing import Any, AsyncGenerator, Callable, Coroutine, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.db import DatabaseSessionManager
from app.chat.services import ChatService
from app.coder.schemas import (
    AIMessageCompletedEvent,
    CoderEvent,
    WorkflowErrorEvent,
    UsageMetricsUpdatedEvent,
    AgentStateEvent,
)
from app.agents.services import WorkflowService
from app.usage.event_handlers import UsageCollector
from app.coder.services.messaging import MessagingTurnEventHandler

logger = logging.getLogger(__name__)


class CoderService:
    def __init__(
        self,
        db: DatabaseSessionManager, # this is not a session, but the manager
        chat_service_factory: Callable[[AsyncSession], Awaitable[ChatService]],
        workflow_service_factory: Callable[[AsyncSession], Awaitable[WorkflowService]],
        agent_factory: Callable[[AsyncSession, int], Coroutine[Any, Any, Any]],
        usage_service_factory: Callable[[AsyncSession], Awaitable[Any]],
        turn_handler_factory: Callable[[], Awaitable[MessagingTurnEventHandler]],
    ):
        self.db = db
        self.chat_service_factory = chat_service_factory
        self.agent_factory = agent_factory
        self.workflow_service_factory = workflow_service_factory
        self.usage_service_factory = usage_service_factory
        self.turn_handler_factory = turn_handler_factory

    async def handle_user_message(
        self, *, user_message: str, session_id: int
    ) -> AsyncGenerator[CoderEvent, None]:
        # 1. Init Event Handler (Stateful for this turn, includes Accumulator)
        messaging_turn_handler = await self.turn_handler_factory()
        
        yield AgentStateEvent(status="Thinking...")

        async with UsageCollector() as event_collector:
            async with self.db.session() as session:
                workflow = await self.agent_factory(session, session_id)

                workflow_service = await self.workflow_service_factory(session)
                
                ctx = await workflow_service.get_context(session_id, workflow)

                chat_service = await self.chat_service_factory(session)
                chat_history = await chat_service.get_chat_history(session_id)

            try:
                handler = workflow.run(
                    user_msg=user_message, chat_history=chat_history, ctx=ctx, max_iterations=settings.AGENT_MAX_ITERATIONS
                )

                async for event in handler.stream_events():
                    async for coder_event in messaging_turn_handler.handle(event):
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
                    
                    await chat_service.save_turn(
                        session_id=session_id,
                        user_content=user_message,
                        blocks=messaging_turn_handler.accumulator.get_blocks(),
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
