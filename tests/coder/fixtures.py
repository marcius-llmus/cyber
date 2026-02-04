import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from app.coder.presentation import WebSocketOrchestrator
from app.coder.services.coder import CoderService
from app.coder.services.execution_registry import TurnExecution, TurnExecutionRegistry
from app.coder.services.messaging import MessagingTurnEventHandler
from app.coder.services.single_shot_patching import SingleShotPatchService


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
    return mocker.create_autospec(MessagingTurnEventHandler, instance=True)


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


@pytest.fixture
def coder_service(mocker: MockerFixture, db_sessionmanager_mock) -> CoderService:
    """CoderService wired with mocked factories (db manager stays a mock)."""
    return CoderService(
        db=db_sessionmanager_mock,
        chat_service_factory=AsyncMock(),
        session_service_factory=AsyncMock(),
        workflow_service_factory=AsyncMock(),
        agent_factory=AsyncMock(),
        usage_service_factory=AsyncMock(),
        turn_handler_factory=AsyncMock(),
        turn_service_factory=AsyncMock(),
        diff_patch_service_factory=AsyncMock(),
        context_service_factory=AsyncMock(),
        single_shot_patch_service_factory=AsyncMock(),
        execution_registry=mocker.create_autospec(TurnExecutionRegistry, instance=True),
    )


@pytest.fixture
def single_shot_patch_service(
    mocker: MockerFixture, db_sessionmanager_mock
) -> SingleShotPatchService:
    return SingleShotPatchService(
        db=db_sessionmanager_mock,
        diff_patch_service_factory=AsyncMock(),
        context_service_factory=AsyncMock(),
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
