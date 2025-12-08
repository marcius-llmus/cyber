from llama_index.core.workflow import Context, Workflow

from app.agents.repositories import WorkflowStateRepository
from app.context.services import RepoMapService, WorkspaceService, CodebaseService
from app.projects.services import ProjectService
from app.context.schemas import FileStatus
from app.agents.constants import (
    AGENT_IDENTITY,
    TOOL_USAGE_RULES,
    OPERATING_PROTOCOL,
    REPO_MAP_DESCRIPTION,
    ACTIVE_CONTEXT_DESCRIPTION,
)


class WorkflowService:
    def __init__(self, workflow_repo: WorkflowStateRepository):
        self.workflow_repo = workflow_repo

    async def get_context(self, session_id: int, workflow: Workflow) -> Context:
        """Hydrates a Context from the DB or creates a new one if none exists."""
        state_record = await self.workflow_repo.get_by_session_id(session_id)
        if state_record and state_record.state:
            return Context.from_dict(workflow, state_record.state)
        return Context(workflow)

    async def save_context(self, session_id: int, context: Context) -> None:
        """Persists the current Context state to the DB."""
        await self.workflow_repo.save_state(session_id, context.to_dict())


class AgentContextService:
    """
    Service responsible for assembling the context and system prompt for the Agent.
    It orchestrates the retrieval of the Repo Map (Tier 1) and Active File Content (Tier 2).
    """
    def __init__(
        self,
        repo_map_service: RepoMapService,
        workspace_service: WorkspaceService,
        codebase_service: CodebaseService,
        project_service: ProjectService,
    ):
        self.repo_map_service = repo_map_service
        self.workspace_service = workspace_service
        self.codebase_service = codebase_service
        self.project_service = project_service

    async def build_system_prompt(self, session_id: int) -> str:
        repo_map = await self.repo_map_service.generate_repo_map(
            session_id=session_id,
            include_active_content=False
        )

        active_context_xml = await self._build_active_context_xml(session_id)

        parts = [
            f"<identity>\n{AGENT_IDENTITY}\n</identity>",
            f"<rules>\n{TOOL_USAGE_RULES}\n{OPERATING_PROTOCOL}\n</rules>",
            f"<repository_map>\n<!-- {REPO_MAP_DESCRIPTION} -->\n{repo_map}\n</repository_map>",
            f"<active_context>\n<!-- {ACTIVE_CONTEXT_DESCRIPTION} -->\n{active_context_xml}\n</active_context>",
        ]

        return "\n\n".join(parts)

    async def _build_active_context_xml(self, session_id: int) -> str:
        project = await self.project_service.get_active_project()
        if not project:
            return ""

        active_files = await self.workspace_service.get_active_context(session_id)
        if not active_files:
            return ""

        xml_parts = []
        for context_file in active_files:
            result = await self.codebase_service.read_file(project.path, context_file.file_path)
            if result.status == FileStatus.SUCCESS:
                xml_parts.append(
                    f'    <file path="{context_file.file_path}">\n{result.content}\n    </file>'
                )
        
        return "\n\n".join(xml_parts)
