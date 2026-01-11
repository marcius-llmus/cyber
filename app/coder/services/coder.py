import logging
from typing import Any, AsyncGenerator, AsyncIterator, Callable, Coroutine, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession

from app.context.services import WorkspaceService
from app.context.schemas import ContextFileListItem
from app.core.config import settings
from app.core.db import DatabaseSessionManager
from app.chat.services import ChatService, ChatTurnService
from app.coder.schemas import (
    CoderEvent,
    WorkflowErrorEvent,
    UsageMetricsUpdatedEvent,
    AgentStateEvent,
    WorkflowLogEvent,
    LogLevel,
    SingleShotDiffAppliedEvent,
    ContextFilesUpdatedEvent,
)
from app.agents.services import WorkflowService
from app.usage.event_handlers import UsageCollector
from app.coder.services.messaging import MessagingTurnEventHandler
from app.sessions.services import SessionService
from app.core.enums import OperationalMode

logger = logging.getLogger(__name__)


class CoderService:
    def __init__(
        self,
        db: DatabaseSessionManager, # this is not a session, but the manager
        chat_service_factory: Callable[[AsyncSession], Awaitable[ChatService]],
        session_service_factory: Callable[[AsyncSession], Awaitable[SessionService]],
        workflow_service_factory: Callable[[AsyncSession], Awaitable[WorkflowService]],
        agent_factory: Callable[[AsyncSession, int, str], Coroutine[Any, Any, Any]],
        usage_service_factory: Callable[[AsyncSession], Awaitable[Any]],
        turn_handler_factory: Callable[[], Awaitable[MessagingTurnEventHandler]],
        turn_service_factory: Callable[[AsyncSession], Awaitable[ChatTurnService]],
        diff_patch_service_factory: Callable[[], Awaitable[Any]],
        context_service_factory: Callable[[AsyncSession], Awaitable[WorkspaceService]],
    ):
        self.db = db
        self.chat_service_factory = chat_service_factory
        self.session_service_factory = session_service_factory
        self.agent_factory = agent_factory
        self.workflow_service_factory = workflow_service_factory
        self.usage_service_factory = usage_service_factory
        self.turn_handler_factory = turn_handler_factory
        self.turn_service_factory = turn_service_factory
        self.diff_patch_service_factory = diff_patch_service_factory
        self.context_service_factory = context_service_factory

    async def handle_user_message(
        self, *, user_message: str, session_id: int, turn_id: str | None = None
    ) -> tuple[str, AsyncIterator[CoderEvent]]:
        # todo: turn_id and session_id will be refactored to support multiple simultaneous sessions
        turn_id = await self._start_turn(session_id=session_id, turn_id=turn_id)

        async def _stream() -> AsyncGenerator[CoderEvent, None]:
            # 1. Init Event Handler (Stateful for this turn, includes Accumulator)
            messaging_turn_handler = await self.turn_handler_factory()

            yield AgentStateEvent(status="Thinking...")

            async with UsageCollector() as event_collector:
                workflow = await self._build_workflow(session_id=session_id, turn_id=turn_id)
                ctx = await self._get_workflow_context(session_id=session_id, workflow=workflow)
                chat_history = await self._get_chat_history(session_id=session_id)

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

                    # this workflow awaits the agent to finish
                    await handler

                    # session here is the db session
                    # session_id is the 'ChatSession', the one user can delete, not db
                    async with self.db.session() as session:
                        chat_service = await self.chat_service_factory(session)
                        session_service = await self.session_service_factory(session)

                        effective_mode = await session_service.get_operational_mode(session_id=session_id)
                        logger.info("Session %s effective operational mode: %s", session_id, effective_mode)

                        # it returns only AI message
                        ai_message = await chat_service.save_messages_for_turn(
                            session_id=session_id,
                            user_content=user_message,
                            blocks=messaging_turn_handler.get_blocks(),
                            turn_id=turn_id,
                        )
                        ai_blocks = list(ai_message.blocks or [])

                    await self._mark_turn_succeeded(session_id=session_id, turn_id=turn_id)

                    if effective_mode == OperationalMode.SINGLE_SHOT:
                        yield AgentStateEvent(status="Applying patches...")
                        # todo: must make it concurrent
                        async for event in self._process_single_shot_diffs(
                            session_id=session_id,
                            turn_id=turn_id,
                            blocks=ai_blocks,
                        ):
                            yield event
                        yield AgentStateEvent(status="")

                    async for usage_event in self._process_new_usage(session_id, event_collector):
                        yield usage_event

                except Exception as e:
                    yield await self._handle_workflow_exception(e, original_message=user_message)
                finally:
                    # Safety check: Log if any events were left behind (e.g., due to a crash before final save)
                    unprocessed_count = event_collector.unprocessed_count
                    if unprocessed_count > 0:
                        logger.warning(f"Session {session_id}: {unprocessed_count} usage events were not processed/persisted.")

        return turn_id, _stream()

    async def _build_workflow(self, *, session_id: int, turn_id: str) -> Any:
        async with self.db.session() as session:
            return await self.agent_factory(session, session_id, turn_id)

    async def _get_workflow_context(self, *, session_id: int, workflow: Any) -> Any:
        async with self.db.session() as session:
            workflow_service = await self.workflow_service_factory(session)
            return await workflow_service.get_context(session_id, workflow)

    async def _get_chat_history(self, *, session_id: int) -> Any:
        async with self.db.session() as session:
            chat_service = await self.chat_service_factory(session) # db session
            return await chat_service.get_chat_history(session_id) # chat session (unrelated to db)

    async def _process_single_shot_diffs(
        self,
        *,
        session_id: int,
        turn_id: str,
        blocks: list[dict[str, Any]],
    ) -> AsyncGenerator[CoderEvent, None]:
        diff_patch_service = await self.diff_patch_service_factory()

        results: list[dict[str, Any]] = []
        parsed_patches = []

        extracted = diff_patch_service.extract_diffs_from_blocks(
            turn_id=turn_id,
            session_id=session_id,
            blocks=blocks,
        )

        for diff_patch in extracted:
            diff_patch_file_path = diff_patch.parsed.path
            parsed_patches.append(diff_patch.parsed)

            result = await diff_patch_service.process_diff(diff_patch)
            results.append(result)

            yield SingleShotDiffAppliedEvent(
                file_path=diff_patch_file_path,
                output=str(result),
            )

        # we must make sure that created and deleted files
        # are added and remove from active context
        if parsed_patches:
            async with self.db.session() as session:
                context_service = await self.context_service_factory(session)
                for patch in parsed_patches:
                    try:
                        await context_service.sync_context_for_diff(
                            session_id=session_id,
                            patch=patch,
                        )
                    except Exception as e:
                        yield WorkflowLogEvent(
                            message=(
                                "Failed to sync context from diff "
                                f"(session_id={session_id}): {e}"
                            ),
                            level=LogLevel.ERROR,
                        )

                files = await context_service.get_active_context(session_id)
                files_data = [
                    ContextFileListItem(id=f.id, file_path=f.file_path)
                    for f in files
                ]

            yield ContextFilesUpdatedEvent(session_id=session_id, files=files_data)

        logger.info(
            "Processed %s SINGLE_SHOT diff patch(es) for turn_id=%s session_id=%s",
            len(results),
            turn_id,
            session_id,
        )

    async def _start_turn(self, *, session_id: int, turn_id: str | None) -> str:
        async with self.db.session() as session:
            turn_service = await self.turn_service_factory(session)
            return await turn_service.start_turn(session_id=session_id, turn_id=turn_id)

    async def _mark_turn_succeeded(self, *, session_id: int, turn_id: str) -> None:
        async with self.db.session() as session:
            turn_service = await self.turn_service_factory(session)
            await turn_service.mark_succeeded(session_id=session_id, turn_id=turn_id)

    async def _process_new_usage(self, session_id: int, collector: UsageCollector) -> AsyncGenerator[CoderEvent, None]:
        """Helper to consume new events from collector and yield metrics updates."""
        new_events = collector.consume()
        if not new_events:
            return

        async with self.db.session() as session:
            usage_service = await self.usage_service_factory(session)
            metrics = await usage_service.process_batch(session_id, new_events)

        # not so cool to process like this, but considering we must process
        # globally dispatched events in batch, this is the wae o7
        if metrics.errors:
            for error in metrics.errors:
                yield WorkflowLogEvent(message=f"Usage Tracking Error: {error}", level=LogLevel.ERROR)

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
