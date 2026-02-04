import pytest
from unittest.mock import AsyncMock, MagicMock
from pytest_mock import MockerFixture
from app.coder.services.coder import CoderService
from app.coder.services.execution_registry import TurnExecutionRegistry, TurnExecution
from app.coder.presentation import WebSocketOrchestrator
from app.chat.schemas import Turn
from app.coder.services.messaging import MessagingTurnEventHandler

@pytest.fixture
def turn_execution_registry() -> TurnExecutionRegistry:
    return TurnExecutionRegistry()

@pytest.fixture
def mock_coder_service(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(CoderService, instance=True)

@pytest.fixture
def mock_websocket_manager(mocker: MockerFixture) -> MagicMock:
    return mocker.MagicMock()

@pytest.fixture
def mock_turn_execution(mocker: MockerFixture) -> MagicMock:
    execution = mocker.create_autospec(TurnExecution, instance=True)
    execution.stream = AsyncMock()
    execution.turn = MagicMock(spec=Turn)
    execution.turn.turn_id = "test-turn-id"
    return execution

@pytest.fixture
def mock_messaging_handler(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(MessagingTurnEventHandler, instance=True)

@pytest.fixture
def websocket_orchestrator(
    mock_websocket_manager, 
    mock_coder_service
) -> WebSocketOrchestrator:
    return WebSocketOrchestrator(
        ws_manager=mock_websocket_manager,
        session_id=1,
        coder_service=mock_coder_service
    )
