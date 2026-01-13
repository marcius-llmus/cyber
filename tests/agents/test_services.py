"""Service tests for the agents app."""

from unittest.mock import MagicMock, AsyncMock

import pytest
from llama_index.core.workflow import Context

from app.agents.models import WorkflowState
from app.agents.repositories import WorkflowStateRepository
from app.agents.services import WorkflowService, AgentContextService
from app.context.models import ContextFile
from app.context.schemas import FileStatus, FileReadResult
from app.core.enums import OperationalMode
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.models import Project
from app.prompts.models import Prompt


class TestWorkflowService:
    @pytest.mark.asyncio
    async def test_get_context_hydrates_existing_context(
        self,
        workflow_service: WorkflowService,
        workflow_state_repository: WorkflowStateRepository,
        workflow_mock: MagicMock,
    ):
        """Should hydrate a workflow Context from stored state when a record exists."""
        session_id = 1
        state_data = {"step": 1}
        # Use AsyncMock for async methods
        workflow_state_repository.get_by_session_id = AsyncMock(
            return_value=WorkflowState(session_id=session_id, state=state_data)
        )
        # Ensure workflow_mock has attributes expected by Context if any
        workflow_mock._timeout = 10.0

        context = await workflow_service.get_context(session_id, workflow_mock)

        assert isinstance(context, Context)

        workflow_state_repository.get_by_session_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_get_context_creates_new_context_when_missing(
        self,
        workflow_service: WorkflowService,
        workflow_state_repository: WorkflowStateRepository,
        workflow_mock: MagicMock,
    ):
        """Should create a new workflow Context when no stored state exists."""
        session_id = 1
        workflow_state_repository.get_by_session_id = AsyncMock(return_value=None)
        workflow_mock._timeout = 10.0

        context = await workflow_service.get_context(session_id, workflow_mock)

        assert isinstance(context, Context)
        workflow_state_repository.get_by_session_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_get_context_calls_repository_with_session_id(
        self,
        workflow_service: WorkflowService,
        workflow_state_repository: WorkflowStateRepository,
        workflow_mock: MagicMock,
    ):
        """get_context should call WorkflowStateRepository.get_by_session_id with the given session_id."""
        session_id = 123
        workflow_state_repository.get_by_session_id = AsyncMock(return_value=None)
        workflow_mock._timeout = 10.0

        await workflow_service.get_context(session_id, workflow_mock)

        workflow_state_repository.get_by_session_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_save_context_persists_state(
        self,
        workflow_service: WorkflowService,
        workflow_state_repository: WorkflowStateRepository,
        workflow_mock: MagicMock,
    ):
        """Should persist the Context state via the repository."""
        session_id = 1
        workflow_mock._timeout = 10.0
        # Context constructor does not take timeout
        context = Context(workflow_mock)

        workflow_state_repository.save_state = AsyncMock()

        await workflow_service.save_context(session_id, context)

        workflow_state_repository.save_state.assert_called_once()
        args = workflow_state_repository.save_state.call_args
        assert args[0][0] == session_id
        assert isinstance(args[0][1], dict)

    @pytest.mark.asyncio
    async def test_save_context_propagates_repository_errors(
        self,
        workflow_service: WorkflowService,
        workflow_state_repository: WorkflowStateRepository,
        workflow_mock: MagicMock,
    ):
        """save_context should surface exceptions raised by WorkflowStateRepository.save_state."""
        session_id = 1
        workflow_mock._timeout = 10.0
        context = Context(workflow_mock)
        workflow_state_repository.save_state = AsyncMock(side_effect=ValueError("DB Error"))

        with pytest.raises(ValueError, match="DB Error"):
            await workflow_service.save_context(session_id, context)


class TestAgentContextService:
    @pytest.mark.asyncio
    async def test_build_system_prompt_raises_when_no_active_project(
        self, agent_context_service: AgentContextService, project_service_mock: MagicMock
    ):
        """Should raise ActiveProjectRequiredException when there is no active project."""
        project_service_mock.get_active_project.return_value = None
        
        with pytest.raises(ActiveProjectRequiredException):
            await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)

    @pytest.mark.asyncio
    async def test_build_system_prompt_chat_mode_is_minimal(
        self, agent_context_service: AgentContextService, project_service_mock: MagicMock
    ):
        """CHAT mode should not include repo map, active context, or tool rules."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
 
        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CHAT)
 
        assert "<IDENTITY>" in prompt
        assert "<PROMPT_STRUCTURE>" in prompt
        # In CHAT mode we only emit IDENTITY + PROMPT_STRUCTURE. The prompt structure
        # text itself mentions the <REPOSITORY_MAP> tag, so we assert that the actual
        # section wrapper is not included.
        assert "<REPOSITORY_MAP>\n" not in prompt
        # Same for ACTIVE_CONTEXT: the prompt structure description contains the literal tag.
        assert "<ACTIVE_CONTEXT>\n" not in prompt
        assert "<RULES>\n" not in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_includes_repo_map_and_active_context_in_coding_mode(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        repo_map_service_mock: MagicMock,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
    ):
        """CODING mode should include both the repo map and active context when available."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        repo_map_service_mock.generate_repo_map.return_value = "tree"
        workspace_service_mock.get_active_context.return_value = [ContextFile(file_path="a.py")]
        # Fix FileReadResult instantiation
        codebase_service_mock.read_file.return_value = FileReadResult(file_path="a.py", status=FileStatus.SUCCESS, content="code")

        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)

        assert "<REPOSITORY_MAP>" in prompt
        assert "<ACTIVE_CONTEXT>" in prompt
        assert "tree" in prompt
        assert "code" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_includes_repo_map_in_ask_mode(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        repo_map_service_mock: MagicMock,
    ):
        """ASK mode should include repo map when available and respect read-only constraints."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        repo_map_service_mock.generate_repo_map.return_value = "tree"

        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.ASK)

        assert "<REPOSITORY_MAP>" in prompt
        assert "tree" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_ask_mode_includes_tool_rules(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
    ):
        """ASK mode should include tool usage rules since read-only tools are available."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        
        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.ASK)
        
        assert "<RULES>" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_includes_repo_map_in_planner_mode(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        repo_map_service_mock: MagicMock,
    ):
        """PLANNER mode should include repo map when available and not require patcher tooling."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        repo_map_service_mock.generate_repo_map.return_value = "tree"

        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.PLANNER)

        assert "<REPOSITORY_MAP>" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_single_shot_mode_excludes_tool_rules(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
    ):
        """SINGLE_SHOT mode should exclude tool usage rules since no tools are available."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
 
        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.SINGLE_SHOT)
 
        # single-shot has no tools
        # Prompt structure text mentions <RULES>, so check the wrapper tag.
        assert "<RULES>\n" not in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_planner_mode_includes_tool_rules(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
    ):
        """PLANNER mode should include tool usage rules since read-only tools are available."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        
        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.PLANNER)
        
        assert "<RULES>" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_includes_guidelines_in_non_chat_modes(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
    ):
        """Non-CHAT modes should include coder behavior guidelines."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        
        for mode in [OperationalMode.CODING, OperationalMode.ASK, OperationalMode.PLANNER, OperationalMode.SINGLE_SHOT]:
            prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=mode)
            assert "<GUIDELINES>" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_includes_custom_prompts_when_present(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        prompt_service_mock: MagicMock,
    ):
        """Non-CHAT modes should embed active prompts XML when prompts exist for the project."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        prompt_service_mock.get_active_prompts.return_value = [Prompt(name="P1", content="C1")]

        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)

        assert "<CUSTOM_INSTRUCTIONS>" in prompt
        assert '<INSTRUCTION name="P1">' in prompt
        assert "C1" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_excludes_custom_prompts_when_absent(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        prompt_service_mock: MagicMock,
    ):
        """Non-CHAT modes should omit CUSTOM_INSTRUCTIONS section when no active prompts exist."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        prompt_service_mock.get_active_prompts.return_value = []

        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)

        # Prompt structure text includes the literal '<CUSTOM_INSTRUCTIONS>' tag in its description.
        # Assert the actual wrapper section is not present.
        assert "<CUSTOM_INSTRUCTIONS>\n" not in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_omits_active_context_when_no_active_files(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        workspace_service_mock: MagicMock,
    ):
        """Non-CHAT modes should omit ACTIVE_CONTEXT when workspace has no active files."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        workspace_service_mock.get_active_context.return_value = []

        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)

        assert "<ACTIVE_CONTEXT>\n" not in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_omits_repo_map_when_repo_map_service_returns_empty(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        repo_map_service_mock: MagicMock,
    ):
        """Non-CHAT modes should omit REPOSITORY_MAP section when repo map is unavailable."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        repo_map_service_mock.generate_repo_map.return_value = None

        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)

        assert "<REPOSITORY_MAP>\n" not in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_active_context_filters_non_successful_file_reads(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
    ):
        """Active context builder should only include files that were read successfully."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        workspace_service_mock.get_active_context.return_value = [
            ContextFile(file_path="good.py"),
            ContextFile(file_path="bad.py"),
        ]
        
        async def read_side_effect(path, file_path):
            if file_path == "good.py":
                return FileReadResult(file_path=file_path, status=FileStatus.SUCCESS, content="good code")
            return FileReadResult(file_path=file_path, status=FileStatus.ERROR, content="")
            
        codebase_service_mock.read_file.side_effect = read_side_effect

        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)

        assert "good.py" in prompt
        assert "bad.py" not in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_sections_order_is_stable(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        repo_map_service_mock: MagicMock,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
        prompt_service_mock: MagicMock,
    ):
        """build_system_prompt should produce sections in a stable, predictable order."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        repo_map_service_mock.generate_repo_map.return_value = "MAP"
        workspace_service_mock.get_active_context.return_value = [ContextFile(file_path="f.py")]
        codebase_service_mock.read_file.return_value = FileReadResult(file_path="f.py", status=FileStatus.SUCCESS, content="CODE")
        prompt_service_mock.get_active_prompts.return_value = [Prompt(name="P", content="C")]

        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)

        # Use exact wrappers so we don't match tag mentions inside the prompt structure text.
        idx_identity = prompt.find("<IDENTITY>\n")
        idx_structure = prompt.find("<PROMPT_STRUCTURE>\n")
        idx_rules = prompt.find("<RULES>\n")
        idx_guidelines = prompt.find("<GUIDELINES>\n")
        idx_custom = prompt.find("<CUSTOM_INSTRUCTIONS>\n")
        idx_context = prompt.find("<ACTIVE_CONTEXT>\n")
        idx_map = prompt.find("<REPOSITORY_MAP>\n")

        assert idx_identity != -1
        assert idx_structure != -1
        assert idx_rules != -1
        assert idx_guidelines != -1
        assert idx_custom != -1
        assert idx_context != -1
        assert idx_map != -1

        assert idx_identity < idx_structure < idx_rules < idx_guidelines < idx_custom < idx_context < idx_map

    @pytest.mark.asyncio
    async def test_build_system_prompt_repo_map_includes_description_comment(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        repo_map_service_mock: MagicMock,
    ):
        """REPOSITORY_MAP section should include the descriptive HTML comment."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        repo_map_service_mock.generate_repo_map.return_value = "MAP"
        
        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)
        
        assert "<!--" in prompt
        assert "AUTHORITATIVE source of truth" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_active_context_includes_description_comment(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
    ):
        """ACTIVE_CONTEXT section should include the descriptive HTML comment."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        workspace_service_mock.get_active_context.return_value = [ContextFile(file_path="f.py")]
        codebase_service_mock.read_file.return_value = FileReadResult(file_path="f.py", status=FileStatus.SUCCESS, content="CODE")
        
        prompt = await agent_context_service.build_system_prompt(session_id=1, operational_mode=OperationalMode.CODING)
        
        assert "<!--" in prompt
        assert "FULL CONTENT of the files" in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_propagates_repo_map_service_errors(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        repo_map_service_mock: MagicMock,
    ):
        """build_system_prompt should surface exceptions raised by RepoMapService.generate_repo_map."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        repo_map_service_mock.generate_repo_map.side_effect = Exception("Repo Map Error")
        
        with pytest.raises(Exception, match="Repo Map Error"):
            await agent_context_service.build_system_prompt(session_id=1)

    @pytest.mark.asyncio
    async def test_build_system_prompt_propagates_workspace_service_errors(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        workspace_service_mock: MagicMock,
    ):
        """build_system_prompt should surface exceptions raised by WorkspaceService.get_active_context."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        workspace_service_mock.get_active_context.side_effect = Exception("Workspace Error")
        
        with pytest.raises(Exception, match="Workspace Error"):
            await agent_context_service.build_system_prompt(session_id=1)

    @pytest.mark.asyncio
    async def test_build_system_prompt_propagates_codebase_service_errors(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
    ):
        """build_system_prompt should surface exceptions raised by CodebaseService.read_file."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        workspace_service_mock.get_active_context.return_value = [ContextFile(file_path="f.py")]
        codebase_service_mock.read_file.side_effect = Exception("Codebase Error")
        
        with pytest.raises(Exception, match="Codebase Error"):
            await agent_context_service.build_system_prompt(session_id=1)

    @pytest.mark.asyncio
    async def test_build_active_context_xml_returns_empty_when_workspace_returns_none(
        self,
        agent_context_service: AgentContextService,
        workspace_service_mock: MagicMock,
    ):
        """_build_active_context_xml should return empty string when workspace returns no active files."""
        workspace_service_mock.get_active_context.return_value = []
        project = Project(id=1, name="p", path="/")
        
        result = await agent_context_service._build_active_context_xml(session_id=1, project=project)
        assert result == ""

    @pytest.mark.asyncio
    async def test_build_active_context_xml_skips_files_with_non_successful_reads(
        self,
        agent_context_service: AgentContextService,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
    ):
        """_build_active_context_xml should skip entries where read_file status is not SUCCESS."""
        workspace_service_mock.get_active_context.return_value = [ContextFile(file_path="bad.py")]
        codebase_service_mock.read_file.return_value = FileReadResult(file_path="bad.py", status=FileStatus.ERROR, content="")
        project = Project(id=1, name="p", path="/")
        
        result = await agent_context_service._build_active_context_xml(session_id=1, project=project)
        assert result == ""

    @pytest.mark.asyncio
    async def test_build_active_context_xml_handles_duplicate_paths(
        self,
        agent_context_service: AgentContextService,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
    ):
        """_build_active_context_xml should define behavior for duplicate file paths (include or dedupe)."""
        # The current implementation iterates over the list returned by workspace_service.
        # If workspace service returns duplicates, it will process duplicates.
        # Ideally workspace service handles this, but let's see what happens here.
        # The requirement asks to test behavior.
        workspace_service_mock.get_active_context.return_value = [
            ContextFile(file_path="a.py"),
            ContextFile(file_path="a.py"),
        ]
        codebase_service_mock.read_file.return_value = FileReadResult(file_path="a.py", status=FileStatus.SUCCESS, content="code")
        project = Project(id=1, name="p", path="/")
        
        result = await agent_context_service._build_active_context_xml(session_id=1, project=project)
        # It should probably include it twice if the service blindly iterates
        assert result.count('<FILE path="a.py">') == 2

    @pytest.mark.asyncio
    async def test_build_active_context_xml_includes_file_tag_with_path_attribute(
        self,
        agent_context_service: AgentContextService,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
    ):
        """_build_active_context_xml should wrap each file in a <FILE path="..."> tag."""
        workspace_service_mock.get_active_context.return_value = [ContextFile(file_path="a.py")]
        codebase_service_mock.read_file.return_value = FileReadResult(file_path="a.py", status=FileStatus.SUCCESS, content="code")
        project = Project(id=1, name="p", path="/")
        
        result = await agent_context_service._build_active_context_xml(session_id=1, project=project)
        assert '<FILE path="a.py">' in result
        assert '</FILE>' in result

    @pytest.mark.asyncio
    async def test_build_active_context_xml_preserves_file_content_exactly(
        self,
        agent_context_service: AgentContextService,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
    ):
        """_build_active_context_xml should embed file content without mutation."""
        content = "def foo():\n    return 1"
        workspace_service_mock.get_active_context.return_value = [ContextFile(file_path="a.py")]
        codebase_service_mock.read_file.return_value = FileReadResult(file_path="a.py", status=FileStatus.SUCCESS, content=content)
        project = Project(id=1, name="p", path="/")
        
        result = await agent_context_service._build_active_context_xml(session_id=1, project=project)
        assert content in result

    @pytest.mark.asyncio
    async def test_build_prompts_xml_wraps_each_prompt_in_instruction_tag(
        self,
        agent_context_service: AgentContextService,
        prompt_service_mock: MagicMock,
    ):
        """_build_prompts_xml should wrap each prompt in an <INSTRUCTION name="..."> tag."""
        prompt_service_mock.get_active_prompts.return_value = [Prompt(name="P1", content="C1")]
        
        result = await agent_context_service._build_prompts_xml(project_id=1)
        assert '<INSTRUCTION name="P1">' in result
        assert '</INSTRUCTION>' in result

    @pytest.mark.asyncio
    async def test_build_prompts_xml_preserves_prompt_content(
        self,
        agent_context_service: AgentContextService,
        prompt_service_mock: MagicMock,
    ):
        """_build_prompts_xml should embed prompt content without mutation."""
        prompt_service_mock.get_active_prompts.return_value = [Prompt(name="P1", content="Content")]
        
        result = await agent_context_service._build_prompts_xml(project_id=1)
        assert "Content" in result

    @pytest.mark.asyncio
    async def test_build_prompts_xml_returns_empty_when_no_active_prompts(
        self,
        agent_context_service: AgentContextService,
        prompt_service_mock: MagicMock,
    ):
        """_build_prompts_xml should return empty string when there are no active prompts."""
        prompt_service_mock.get_active_prompts.return_value = []
        
        result = await agent_context_service._build_prompts_xml(project_id=1)
        assert result == ""

    @pytest.mark.asyncio
    async def test_build_system_prompt_excludes_active_context_when_all_reads_fail(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        workspace_service_mock: MagicMock,
        codebase_service_mock: MagicMock,
    ):
        """build_system_prompt should omit ACTIVE_CONTEXT when no files are successfully read."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        workspace_service_mock.get_active_context.return_value = [ContextFile(file_path="f.py")]
        codebase_service_mock.read_file.return_value = FileReadResult(file_path="f.py", status=FileStatus.ERROR, content="")
 
        prompt = await agent_context_service.build_system_prompt(session_id=1)
        assert "<ACTIVE_CONTEXT>\n" not in prompt

    @pytest.mark.asyncio
    async def test_build_system_prompt_excludes_repo_map_when_repo_map_is_none(
        self,
        agent_context_service: AgentContextService,
        project_service_mock: MagicMock,
        repo_map_service_mock: MagicMock,
    ):
        """build_system_prompt should omit REPOSITORY_MAP when repo map service returns None."""
        project_service_mock.get_active_project.return_value = Project(id=1, name="p", path="/")
        repo_map_service_mock.generate_repo_map.return_value = None
        
        prompt = await agent_context_service.build_system_prompt(session_id=1)
        assert "<REPOSITORY_MAP>\n" not in prompt