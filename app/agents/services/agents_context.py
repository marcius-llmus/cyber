from app.agents.constants import (
    ACTIVE_CONTEXT_DESCRIPTION,
    AGENT_IDENTITY,
    ASK_IDENTITY,
    CHAT_IDENTITY,
    CODER_BEHAVIOR,
    PLANNER_IDENTITY,
    PROMPT_STRUCTURE_GUIDE,
    REPO_MAP_DESCRIPTION,
    SINGLE_SHOT_IDENTITY,
    TOOL_USAGE_RULES,
)
from app.context.schemas import FileStatus
from app.context.services import CodebaseService, RepoMapService, WorkspaceService
from app.core.enums import OperationalMode
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.models import Project
from app.projects.services import ProjectService
from app.prompts.services import PromptService


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
        prompt_service: PromptService,
    ):
        self.repo_map_service = repo_map_service
        self.workspace_service = workspace_service
        self.codebase_service = codebase_service
        self.project_service = project_service
        self.prompt_service = prompt_service

    async def build_system_prompt(
        self,
        session_id: int,
        operational_mode: OperationalMode = OperationalMode.CODING,
    ) -> str:
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException(
                "Active project required to build system prompt."
            )

        # Determine Identity and Rules based on Mode
        identity = AGENT_IDENTITY
        rules = TOOL_USAGE_RULES
        guidelines = CODER_BEHAVIOR

        if operational_mode == OperationalMode.ASK:
            identity = ASK_IDENTITY
            # ASK is read-only: no patch/file modifications
            rules = TOOL_USAGE_RULES
            guidelines = CODER_BEHAVIOR

        if operational_mode == OperationalMode.PLANNER:
            identity = PLANNER_IDENTITY
            guidelines = CODER_BEHAVIOR
        elif operational_mode == OperationalMode.SINGLE_SHOT:
            identity = SINGLE_SHOT_IDENTITY
            rules = ""  # No tools in single shot
            guidelines = CODER_BEHAVIOR

        if operational_mode == OperationalMode.CHAT:
            identity = CHAT_IDENTITY
            # CHAT has no tools
            rules = ""
            guidelines = ""

        # CHAT mode: minimal prompt, no context
        if operational_mode == OperationalMode.CHAT:
            return "\n\n".join(
                [
                    f"<IDENTITY>\n{identity}\n</IDENTITY>",
                    f"<PROMPT_STRUCTURE>\n{PROMPT_STRUCTURE_GUIDE}\n</PROMPT_STRUCTURE>",
                ]
            )

        # For other modes, fetch context
        custom_prompts_xml = await self._build_prompts_xml(project.id)

        # fetch repo map (semi-stable)
        repo_map = await self.repo_map_service.generate_repo_map(
            session_id=session_id, include_active_content=False
        )

        # fetch active context (volatile)
        active_context_xml = await self._build_active_context_xml(session_id, project)

        parts = [
            f"<IDENTITY>\n{identity}\n</IDENTITY>",
            f"<PROMPT_STRUCTURE>\n{PROMPT_STRUCTURE_GUIDE}\n</PROMPT_STRUCTURE>",
        ]

        if rules:
            parts.append(f"<RULES>\n{rules}\n</RULES>")

        if guidelines:
            parts.append(f"<GUIDELINES>\n{guidelines}\n</GUIDELINES>")

        if custom_prompts_xml:
            parts.append(
                f"<CUSTOM_INSTRUCTIONS>\n{custom_prompts_xml}\n</CUSTOM_INSTRUCTIONS>"
            )

        if active_context_xml:
            parts.append(
                f"<ACTIVE_CONTEXT>\n<!-- {ACTIVE_CONTEXT_DESCRIPTION} -->\n{active_context_xml}\n</ACTIVE_CONTEXT>"
            )

        if repo_map:
            parts.append(
                f"<REPOSITORY_MAP>\n<!-- {REPO_MAP_DESCRIPTION} -->\n{repo_map}\n</REPOSITORY_MAP>"
            )

        return "\n\n".join(parts)

    async def _build_active_context_xml(self, session_id: int, project: Project) -> str:
        active_files = await self.workspace_service.get_active_context(session_id)
        if not active_files:
            return ""

        file_parts: list[str] = []
        for context_file in active_files:
            result = await self.codebase_service.read_file(
                project.path, context_file.file_path
            )
            if result.status == FileStatus.SUCCESS:
                file_parts.append(
                    f'<FILE path="{context_file.file_path}">\n{result.content}\n</FILE>'
                )

        if not file_parts:
            return ""

        return "<CONTEXT_FILES>\n" + "\n\n".join(file_parts) + "\n</CONTEXT_FILES>"

    async def _build_prompts_xml(self, project_id: int) -> str:
        # todo: later down the road we could make prompts by session no matter the project
        #       and allow user to clone current session so independent prompts but cloned
        prompts = await self.prompt_service.get_active_prompts(project_id)
        if not prompts:
            return ""

        return "\n\n".join(
            [
                f'<INSTRUCTION name="{p.name}">\n{p.content}\n</INSTRUCTION>'
                for p in prompts
            ]
        )
