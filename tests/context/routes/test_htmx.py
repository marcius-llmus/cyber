from unittest.mock import AsyncMock

import pytest


class TestContextHtmxRoutes:

    @pytest.mark.usefixtures("override_get_context_page_service")
    async def test_get_file_tree(self, client, context_page_service_mock, get_file_tree_page_data_mock):
        """GET /session/{id}/file-tree returns the file tree."""
        context_page_service_mock.get_file_tree_page_data = AsyncMock(return_value=get_file_tree_page_data_mock)
        response = client.get("/context/session/1/file-tree", headers={"HX-Request": "true"})
        assert response.status_code == 200

        html = response.text
        assert 'ul class="w-full"' in html
        assert '>root<' in html
        assert '>src<' in html
        assert '>main.py<' in html
        assert 'name="filepaths[]"' in html
        assert 'value="src/main.py"' in html
        assert "checked" in html

        context_page_service_mock.get_file_tree_page_data.assert_awaited_once_with(session_id=1)


    @pytest.mark.usefixtures("override_get_context_service", "override_get_context_page_service")
    async def test_batch_update_context_files(
        self, client, workspace_service_mock, context_page_service_mock
    ):
        """POST /session/{id}/files/batch syncs files and returns updated list."""
        context_page_service_mock.get_context_files_page_data = AsyncMock(return_value={
            "files": [], "session_id": 1
        })
        workspace_service_mock.sync_files = AsyncMock(return_value=None)

        payload = {"filepaths": ["src/main.py", "README.md"]}
        response = client.post(
            "/context/session/1/files/batch",
            json=payload,
            headers={"HX-Request": "true"}
        )

        assert response.status_code == 200
        workspace_service_mock.sync_files.assert_awaited_once_with(1, payload["filepaths"])
        context_page_service_mock.get_context_files_page_data.assert_awaited_once_with(1)

    @pytest.mark.usefixtures("override_get_context_service", "override_get_context_page_service")
    async def test_clear_all_context_files(
        self, client, workspace_service_mock, context_page_service_mock
    ):
        """DELETE /session/{id}/files clears all files."""
        context_page_service_mock.get_context_files_page_data = AsyncMock(return_value={
            "files": [], "session_id": 1
        })
        workspace_service_mock.delete_context_for_session = AsyncMock(return_value=None)

        response = client.delete("/context/session/1/files", headers={"HX-Request": "true"})

        assert response.status_code == 200
        workspace_service_mock.delete_context_for_session.assert_awaited_once_with(1)
        context_page_service_mock.get_context_files_page_data.assert_awaited_once_with(1)

    @pytest.mark.usefixtures("override_get_context_service", "override_get_context_page_service")
    async def test_remove_context_file(
        self, client, workspace_service_mock, context_page_service_mock
    ):
        """DELETE /session/{id}/files/{file_id} removes a single file."""
        context_page_service_mock.get_context_files_page_data = AsyncMock(return_value={
            "files": [], "session_id": 1
        })
        workspace_service_mock.remove_file = AsyncMock(return_value=None)

        response = client.delete("/context/session/1/files/99", headers={"HX-Request": "true"})

        assert response.status_code == 200
        workspace_service_mock.remove_file.assert_awaited_once_with(1, 99)
        context_page_service_mock.get_context_files_page_data.assert_awaited_once_with(1)
