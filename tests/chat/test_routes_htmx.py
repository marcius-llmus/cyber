from app.projects.exceptions import ActiveProjectRequiredException
from app.sessions.models import ChatSession


class TestChatHtmxRoutes:
    async def test_clear_chat_requires_active_project(
        self, client, override_get_chat_service, chat_service_mock
    ):
        """POST /chat/clear raises 400 if no active project is found (ActiveProjectRequiredException)."""
        chat_service_mock.get_or_create_active_session.side_effect = (
            ActiveProjectRequiredException("No project")
        )

        response = client.post("/chat/clear", headers={"HX-Request": "true"})

        assert response.status_code == 400
        assert "No project" in response.text

    def test_clear_chat_clears_session_messages_and_returns_empty_list(
        self, client, override_get_chat_service, chat_service_mock
    ):
        """POST /chat/clear calls chat_service.clear_session_messages and returns the message list partial.

        Note: even with no chat messages, the partial contains the system welcome message.
        """
        session = ChatSession(id=123)
        chat_service_mock.get_or_create_active_session.return_value = session

        response = client.post("/chat/clear", headers={"HX-Request": "true"})

        assert response.status_code == 200
        chat_service_mock.clear_session_messages.assert_awaited_with(session_id=123)
        assert 'id="message-list"' in response.text
        assert "Hello! How can I assist you today?" in response.text
