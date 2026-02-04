import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from app.agents.services import WorkflowService
from app.chat.services import ChatService, ChatTurnService
from app.coder.presentation import WebSocketOrchestrator
from app.coder.services.coder import CoderService
from app.coder.services.execution_registry import TurnExecution, TurnExecutionRegistry
from app.coder.services.messaging import MessagingTurnEventHandler
from app.coder.services.single_shot_patching import SingleShotPatchService
from app.context.services import WorkspaceService
from app.sessions.services import SessionService


@pytest.fixture
def turn_execution_registry() -> TurnExecutionRegistry:
    return TurnExecutionRegistry()


@pytest.fixture
def mock_coder_service(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(CoderService, instance=True)


@dataclass(slots=True)
class FakeWebSocketManager:
    incoming: asyncio.Queue
    sent_html: list[str]

    async def receive_json(self):  # noqa: ANN001
        item = await self.incoming.get()
        if isinstance(item, BaseException):
            raise item
        return item

    async def send_html(self, html: str) -> None:
        self.sent_html.append(html)


class FakeWorkflowHandler:
    """A minimal workflow handler compatible with CoderService.

    Production expects:
      - .stream_events() -> async iterator
      - await handler  (awaitable)
      - .cancel_run() for cancellation
    """

    def __init__(
        self,
        *,
        events: list | None = None,
        await_raises: BaseException | None = None,
    ) -> None:
        self._events = list(events or [])
        self._await_raises = await_raises
        self.cancel_run = AsyncMock()

    async def stream_events(self):  # noqa: ANN001
        for item in self._events:
            yield item

    async def _wait(self) -> None:
        if self._await_raises is not None:
            raise self._await_raises

    def __await__(self):  # noqa: D401
        return self._wait().__await__()


@pytest.fixture
def mock_websocket_manager() -> FakeWebSocketManager:
    return FakeWebSocketManager(incoming=asyncio.Queue(), sent_html=[])


@pytest.fixture
def make_stream():  # noqa: ANN001
    def _factory(items: list):  # noqa: ANN001
        async def _gen() -> AsyncGenerator:  # noqa: ANN001
            for item in items:
                yield item

        return _gen()

    return _factory


@pytest.fixture
def empty_async_gen() -> Callable[[object], AsyncIterator[object]]:
    """Returns an async generator function that yields nothing."""

    async def _empty(_event: object) -> AsyncIterator[object]:
        if False:  # pragma: no cover
            yield _event

    return _empty


@pytest.fixture
def messaging_turn_handler_mock(
    mocker: MockerFixture,
    empty_async_gen: Callable[[object], AsyncIterator[object]],
) -> MagicMock:
    """Mock for MessagingTurnEventHandler with correct sync/async shapes.

    - handle(event): async generator (NOT an AsyncMock)
    - get_blocks(): sync
    """

    handler = mocker.create_autospec(MessagingTurnEventHandler, instance=True)
    handler.handle = empty_async_gen  # type: ignore[method-assign]
    handler.get_blocks.return_value = []
    return handler


@pytest.fixture
def workflow_mock(mocker: MockerFixture, make_workflow_handler):  # noqa: ANN001
    """Workflow mock where .run(...) is synchronous (MagicMock)."""

    workflow = mocker.MagicMock()
    workflow.run = mocker.MagicMock(return_value=make_workflow_handler(events=[]))
    return workflow


@pytest.fixture
def make_turn_execution(mocker: MockerFixture, make_stream):  # noqa: ANN001
    def _factory(
        *,
        turn_id: str = "test-turn-id",
        items: list | None = None,
        user_message: str = "hi",
    ) -> TurnExecution:
        turn = mocker.MagicMock()
        turn.turn_id = turn_id
        turn.settings_snapshot = mocker.MagicMock()
        return TurnExecution(
            turn=turn, stream=make_stream(items or []), user_message=user_message
        )

    return _factory


@pytest.fixture
def make_workflow_handler():  # noqa: ANN001
    def _factory(
        *, events: list | None = None, await_raises: BaseException | None = None
    ) -> FakeWorkflowHandler:
        return FakeWorkflowHandler(events=events, await_raises=await_raises)

    return _factory


@pytest.fixture
def fake_agent_stream_event():  # noqa: ANN001
    """Factory for a minimal AgentStream-like event.

    We avoid instantiating the real `llama_index`/`workflows` Pydantic models in
    unit tests because certain versions can trigger recursion errors when
    attributes are accessed.
    """

    class _FakeAgentStream:
        def __init__(self, delta: str):
            self.delta = delta

    def _factory(delta: str) -> _FakeAgentStream:
        return _FakeAgentStream(delta)

    return _factory


@pytest.fixture
def mock_messaging_handler(mocker: MockerFixture) -> MagicMock:
    """Historical fixture kept for backwards compatibility.

    Prefer `messaging_turn_handler_mock` which ensures the correct async-generator
    shape for `.handle()`.
    """
    handler = mocker.create_autospec(MessagingTurnEventHandler, instance=True)

    async def _empty_handle(_event):  # noqa: ANN001
        if False:  # pragma: no cover
            yield None

    handler.handle = _empty_handle  # type: ignore[method-assign]
    handler.get_blocks.return_value = []
    return handler


@pytest.fixture
def websocket_orchestrator(
    mock_websocket_manager, mock_coder_service
) -> WebSocketOrchestrator:
    return WebSocketOrchestrator(
        ws_manager=mock_websocket_manager,
        session_id=1,
        coder_service=mock_coder_service,
    )


@pytest.fixture
def orchestrator(
    websocket_orchestrator: WebSocketOrchestrator,
) -> WebSocketOrchestrator:
    """Alias fixture to match test parameter names."""
    return websocket_orchestrator


@pytest.fixture
def turn_mock(mocker: MockerFixture) -> MagicMock:
    turn = mocker.MagicMock()
    turn.turn_id = "t1"
    turn.settings_snapshot = mocker.MagicMock()
    turn.settings_snapshot.diff_patch_processor_type = "codex"
    return turn


@pytest.fixture
def messaging_handler(turn_mock: MagicMock) -> MessagingTurnEventHandler:
    return MessagingTurnEventHandler(turn=turn_mock)


@pytest.fixture
def handler(messaging_handler: MessagingTurnEventHandler) -> MessagingTurnEventHandler:
    """Alias fixture to match historical test parameter name."""
    return messaging_handler


# the megazord fixtures (because it centralizes the CODER websocket)
@pytest.fixture
def coder_service(
    mocker: MockerFixture,
    db_sessionmanager_mock,
    turn_execution_registry: TurnExecutionRegistry,
    messaging_turn_handler_mock: MagicMock,
    workflow_mock: MagicMock,
) -> CoderService:
    default_turn = mocker.MagicMock()
    default_turn.turn_id = "t1"
    default_turn.settings_snapshot = mocker.MagicMock()
    default_turn.settings_snapshot.diff_patch_processor_type = "codex"

    default_turn_service = mocker.create_autospec(ChatTurnService, instance=True)
    default_turn_service.start_turn = AsyncMock(return_value=default_turn)
    default_turn_service.mark_succeeded = AsyncMock(return_value=None)
    turn_service_factory = AsyncMock(return_value=default_turn_service)
    turn_handler_factory = AsyncMock(return_value=messaging_turn_handler_mock)
    agent_factory = AsyncMock(return_value=workflow_mock)
    default_workflow_service = mocker.create_autospec(WorkflowService, instance=True)
    default_workflow_service.get_context = AsyncMock(return_value=object())
    workflow_service_factory = AsyncMock(return_value=default_workflow_service)
    default_chat_service = mocker.create_autospec(ChatService, instance=True)
    default_chat_service.get_chat_history = AsyncMock(return_value=[])
    default_chat_service.save_messages_for_turn = AsyncMock(
        return_value=mocker.MagicMock(blocks=[])
    )

    chat_service_factory = AsyncMock(return_value=default_chat_service)

    default_session_service = mocker.create_autospec(SessionService, instance=True)
    default_session_service.get_operational_mode = AsyncMock(return_value=None)

    session_service_factory = AsyncMock(return_value=default_session_service)

    default_usage_service = mocker.MagicMock()
    default_usage_service.process_batch = AsyncMock(
        return_value=mocker.MagicMock(
            errors=[],
            session_cost=0,
            monthly_cost=0,
            input_tokens=0,
            output_tokens=0,
            cached_tokens=0,
        )
    )

    usage_service_factory = AsyncMock(return_value=default_usage_service)

    # --- Default factories for patch/context services (not used unless SINGLE_SHOT) ---
    default_diff_patch_service = mocker.MagicMock()
    default_diff_patch_service.extract_diffs_from_blocks.return_value = []

    diff_patch_service_factory = AsyncMock(return_value=default_diff_patch_service)

    default_workspace_service = mocker.create_autospec(WorkspaceService, instance=True)

    context_service_factory = AsyncMock(return_value=default_workspace_service)

    default_single_shot_patch_service = mocker.create_autospec(
        SingleShotPatchService, instance=True
    )

    single_shot_patch_service_factory = AsyncMock(
        return_value=default_single_shot_patch_service
    )

    return CoderService(
        db=db_sessionmanager_mock,
        chat_service_factory=chat_service_factory,
        session_service_factory=session_service_factory,
        workflow_service_factory=workflow_service_factory,
        agent_factory=agent_factory,
        usage_service_factory=usage_service_factory,
        turn_handler_factory=turn_handler_factory,
        turn_service_factory=turn_service_factory,
        diff_patch_service_factory=diff_patch_service_factory,
        context_service_factory=context_service_factory,
        single_shot_patch_service_factory=single_shot_patch_service_factory,
        execution_registry=turn_execution_registry,
    )


@pytest.fixture
def single_shot_patch_service(
    mocker: MockerFixture, db_sessionmanager_mock
) -> SingleShotPatchService:
    default_diff_patch_service = mocker.MagicMock()
    default_diff_patch_service.extract_diffs_from_blocks.return_value = []

    async def _diff_patch_service_factory():
        return default_diff_patch_service

    default_workspace_service = mocker.create_autospec(WorkspaceService, instance=True)

    async def _context_service_factory(_session):  # noqa: ANN001
        return default_workspace_service

    return SingleShotPatchService(
        db=db_sessionmanager_mock,
        diff_patch_service_factory=_diff_patch_service_factory,
        context_service_factory=_context_service_factory,
    )


@pytest.fixture
def usage_collector_cm(mocker: MockerFixture):  # noqa: ANN001
    """A real async context manager for UsageCollector patching (no mocking magic methods).

    Usage:
        with patch("...UsageCollector", usage_collector_cm):
            ...
    """

    collector = mocker.MagicMock()
    collector.unprocessed_count = 0
    collector.consume.return_value = []

    @asynccontextmanager
    async def _cm():
        yield collector

    _cm.collector = collector  # type: ignore[attr-defined]
    return _cm
