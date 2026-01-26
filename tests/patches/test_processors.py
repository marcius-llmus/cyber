from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.context.schemas import FileReadResult, FileStatus
from app.llms.enums import LLMModel
from app.patches.services.processors.udiff_processor import UDiffProcessor
from app.projects.exceptions import ActiveProjectRequiredException


class TestUDiffProcessor:
    def test_strip_markdown_strips_fenced_code_block(self):
        """Should return inner content when response is wrapped in ```...``` fences."""
        assert UDiffProcessor._strip_markdown("```\nhello\n```") == "hello"

    def test_strip_markdown_strips_fenced_code_block_with_language(self):
        """Should strip ```python (or similar) fences and return inner content."""
        assert UDiffProcessor._strip_markdown("```python\nhello\n```") == "hello"

    def test_strip_markdown_returns_original_when_not_fenced(self):
        """Should return input text unchanged if no wrapping fences exist."""
        assert UDiffProcessor._strip_markdown("hello") == "hello"

    async def test_apply_patch_delegates_per_parsed_patch_in_order(
        self, mocker, db_sessionmanager_mock
    ):
        """Should call _apply_file_diff once per extracted ParsedPatch (order preserved)."""
        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        patches = [
            mocker.MagicMock(path="a.txt", diff="d1"),
            mocker.MagicMock(path="b.txt", diff="d2"),
        ]
        mocker.patch(
            "app.patches.services.processors.udiff_processor.UDiffRepresentationExtractor.extract",
            return_value=patches,
        )
        apply_mock = mocker.patch.object(
            processor, "_apply_file_diff", new=AsyncMock(return_value="")
        )

        await processor.apply_patch("RAW")

        assert apply_mock.await_count == 2
        assert apply_mock.await_args_list[0].kwargs["file_path"] == "a.txt"
        assert apply_mock.await_args_list[1].kwargs["file_path"] == "b.txt"

    async def test_apply_patch_noop_when_extractor_returns_empty(
        self, mocker, db_sessionmanager_mock
    ):
        """Should not call _apply_file_diff when no ParsedPatch entries exist."""
        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        mocker.patch(
            "app.patches.services.processors.udiff_processor.UDiffRepresentationExtractor.extract",
            return_value=[],
        )
        apply_mock = mocker.patch.object(processor, "_apply_file_diff", new=AsyncMock())
        await processor.apply_patch("RAW")
        apply_mock.assert_not_awaited()

    async def test_apply_file_diff_raises_when_no_active_project(
        self,
        mocker,
        db_sessionmanager_mock,
        project_service_mock,
        codebase_service_mock,
    ):
        """Should raise ActiveProjectRequiredException if project_service.get_active_project returns None."""
        project_service_mock.get_active_project = AsyncMock(return_value=None)

        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(return_value=project_service_mock),
            codebase_service_factory=AsyncMock(return_value=codebase_service_mock),
        )

        with pytest.raises(ActiveProjectRequiredException):
            await processor._apply_file_diff(file_path="a.txt", diff_content="d")

    async def test_apply_file_diff_raises_for_binary_file(
        self,
        mocker,
        db_sessionmanager_mock,
        project_service_mock,
        codebase_service_mock,
        project,
    ):
        """Should raise ValueError when codebase_service.read_file returns FileStatus.BINARY."""
        project_service_mock.get_active_project = AsyncMock(return_value=project)

        codebase_service_mock.read_file = AsyncMock(
            return_value=FileReadResult(
                file_path="a.txt", status=FileStatus.BINARY, content=""
            )
        )

        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(return_value=mocker.MagicMock()),
            project_service_factory=AsyncMock(return_value=project_service_mock),
            codebase_service_factory=AsyncMock(return_value=codebase_service_mock),
        )

        with pytest.raises(ValueError, match="Cannot patch binary file"):
            await processor._apply_file_diff(file_path="a.txt", diff_content="d")

    async def test_apply_file_diff_raises_for_read_error(
        self,
        mocker,
        db_sessionmanager_mock,
        project_service_mock,
        codebase_service_mock,
        project,
    ):
        """Should raise ValueError when codebase_service.read_file returns FileStatus.ERROR."""
        project_service_mock.get_active_project = AsyncMock(return_value=project)

        codebase_service_mock.read_file = AsyncMock(
            return_value=FileReadResult(
                file_path="a.txt",
                status=FileStatus.ERROR,
                content="",
                error_message="nope",
            )
        )

        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(return_value=mocker.MagicMock()),
            project_service_factory=AsyncMock(return_value=project_service_mock),
            codebase_service_factory=AsyncMock(return_value=codebase_service_mock),
        )

        with pytest.raises(ValueError, match="Could not read file a.txt"):
            await processor._apply_file_diff(file_path="a.txt", diff_content="d")

    async def test_apply_file_diff_calls_llm_client_with_expected_model_and_temperature(
        self,
        mocker,
        db_sessionmanager_mock,
        project_service_mock,
        codebase_service_mock,
        llm_service_mock,
        llm_client_mock,
        project,
    ):
        """Should await llm_service.get_client(model_name=GPT_4_1_MINI, temperature=0)."""
        project_service_mock.get_active_project = AsyncMock(return_value=project)

        codebase_service_mock.read_file = AsyncMock(
            return_value=FileReadResult(
                file_path="a.txt", status=FileStatus.SUCCESS, content="orig"
            )
        )
        codebase_service_mock.write_file = AsyncMock(return_value=None)

        llm_client_mock.achat = AsyncMock(
            return_value=mocker.MagicMock(message=mocker.MagicMock(content="patched"))
        )
        llm_service_mock.get_client = AsyncMock(return_value=llm_client_mock)

        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(return_value=llm_service_mock),
            project_service_factory=AsyncMock(return_value=project_service_mock),
            codebase_service_factory=AsyncMock(return_value=codebase_service_mock),
        )

        await processor._apply_file_diff(file_path="a.txt", diff_content="d")

        llm_service_mock.get_client.assert_awaited_once_with(
            model_name=LLMModel.GPT_4_1_MINI,
            temperature=Decimal("0"),
        )

    async def test_apply_file_diff_writes_patched_content(
        self,
        mocker,
        db_sessionmanager_mock,
        project_service_mock,
        codebase_service_mock,
        llm_service_mock,
        llm_client_mock,
        project,
    ):
        """Should call codebase_service.write_file(project.path, file_path, patched_content)."""

        project_service_mock.get_active_project = AsyncMock(return_value=project)

        codebase_service_mock.read_file = AsyncMock(
            return_value=FileReadResult(
                file_path="a.txt", status=FileStatus.SUCCESS, content="orig"
            )
        )
        codebase_service_mock.write_file = AsyncMock(return_value=None)

        llm_client_mock.achat = AsyncMock(
            return_value=mocker.MagicMock(message=mocker.MagicMock(content="patched"))
        )
        llm_service_mock.get_client = AsyncMock(return_value=llm_client_mock)

        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(return_value=llm_service_mock),
            project_service_factory=AsyncMock(return_value=project_service_mock),
            codebase_service_factory=AsyncMock(return_value=codebase_service_mock),
        )

        await processor._apply_file_diff(file_path="a.txt", diff_content="d")

        codebase_service_mock.write_file.assert_awaited_once_with(
            project.path, "a.txt", "patched"
        )

    async def test_apply_file_diff_reads_file_with_must_exist_false(
        self,
        mocker,
        db_sessionmanager_mock,
        project_service_mock,
        codebase_service_mock,
        llm_service_mock,
        llm_client_mock,
        project,
    ):
        """Should call codebase_service.read_file(..., must_exist=False) to support new files."""

        project_service_mock.get_active_project = AsyncMock(return_value=project)

        codebase_service_mock.read_file = AsyncMock(
            return_value=FileReadResult(
                file_path="a.txt", status=FileStatus.SUCCESS, content="orig"
            )
        )
        codebase_service_mock.write_file = AsyncMock(return_value=None)

        llm_client_mock.achat = AsyncMock(
            return_value=mocker.MagicMock(message=mocker.MagicMock(content="patched"))
        )
        llm_service_mock.get_client = AsyncMock(return_value=llm_client_mock)

        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(return_value=llm_service_mock),
            project_service_factory=AsyncMock(return_value=project_service_mock),
            codebase_service_factory=AsyncMock(return_value=codebase_service_mock),
        )

        await processor._apply_file_diff(file_path="a.txt", diff_content="d")
        codebase_service_mock.read_file.assert_awaited_once_with(
            project.path, "a.txt", must_exist=False
        )

    async def test_apply_via_llm_strips_markdown_from_response(
        self, mocker, db_sessionmanager_mock, llm_client_mock
    ):
        """Should strip markdown fences from llm output before returning."""
        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        llm_client_mock.achat = AsyncMock(
            return_value=mocker.MagicMock(
                message=mocker.MagicMock(content="```\npatched\n```")
            )
        )
        out = await processor._apply_via_llm(llm_client_mock, "orig", "diff")
        assert out == "patched"

    async def test_apply_via_llm_sends_expected_prompt_messages(
        self, mocker, db_sessionmanager_mock, llm_client_mock
    ):
        """Should call llm_client.achat() with system prompt + ORIGINAL CONTENT + DIFF PATCH."""
        processor = UDiffProcessor(
            db=db_sessionmanager_mock,
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        llm_client_mock.achat = AsyncMock(
            return_value=mocker.MagicMock(message=mocker.MagicMock(content="patched"))
        )
        await processor._apply_via_llm(llm_client_mock, "orig", "diff")

        llm_client_mock.achat.assert_awaited_once()
        messages = llm_client_mock.achat.await_args.args[0]
        assert len(messages) == 3
        assert messages[0].role == "system"
        assert "ORIGINAL CONTENT:" in messages[1].content
        assert "DIFF PATCH:" in messages[2].content
