from app.projects.models import Project
from app.projects.exceptions import ActiveProjectRequiredException
from app.blueprints.services import BlueprintService
from app.projects.services import ProjectService
from app.prompts.exceptions import PromptNotFoundException
from app.prompts.repositories import PromptRepository
from app.prompts.schemas import (
    PromptCreate,
    PromptInternalCreate,
    PromptsPageContext,
    PromptUpdate,
)
from app.prompts.enums import PromptType
from app.prompts.models import Prompt


class PromptService:
    def __init__(self, prompt_repo: PromptRepository, project_service: ProjectService):
        self.prompt_repo = prompt_repo
        self.project_service = project_service

    async def get_prompt(self, prompt_id: int) -> Prompt:
        prompt = await self.prompt_repo.get(pk=prompt_id)
        if not prompt:
            raise PromptNotFoundException(f"Prompt with id {prompt_id} not found.")
        return prompt

    async def create_global_prompt(self, prompt_in: PromptCreate) -> Prompt:
        """Creates a global prompt."""
        internal_create = PromptInternalCreate(type=PromptType.GLOBAL, project_id=None, **prompt_in.model_dump())
        return await self.prompt_repo.create(obj_in=internal_create)

    async def create_project_prompt(self, prompt_in: PromptCreate) -> Prompt:
        """Creates a project-specific prompt, ensuring an active project exists."""
        active_project = await self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to create a project prompt.")
        internal_create = PromptInternalCreate(
            type=PromptType.PROJECT, project_id=active_project.id, **prompt_in.model_dump()
        )
        return await self.prompt_repo.create(obj_in=internal_create)

    async def update_prompt(self, prompt_id: int, prompt_in: PromptUpdate) -> Prompt:
        db_obj = await self.get_prompt(prompt_id)
        return await self.prompt_repo.update(db_obj=db_obj, obj_in=prompt_in)

    async def delete_prompt(self, prompt_id: int) -> None:
        await self.get_prompt(prompt_id)  # Ensures the prompt exists before attempting deletion
        await self.prompt_repo.delete(pk=prompt_id)

    async def get_global_prompts(self) -> list[Prompt]:
        return await self.prompt_repo.list_global()

    async def get_project_prompts(self, project: Project | None) -> list[Prompt]:
        if not project:
            return []
        return await self.prompt_repo.list_by_project(project_id=project.id)

    @staticmethod
    async def _generate_blueprint_content(path: str) -> str:
        """
        MOCKED: Generates a blueprint from the given path.
        This will be replaced by a call to a dedicated BlueprintService.
        """
        # This is a placeholder. The real implementation would scan the filesystem.
        return f"Blueprint for: {path}\n\n.gitignore\nREADME.md\napp/\n  __init__.py\n  main.py"

    async def create_or_update_project_blueprint_prompt(self, path: str) -> tuple[Prompt, bool]:
        """
        Generates a blueprint from a path and creates or updates a special prompt
        for the currently active project.
        Returns the prompt and a boolean indicating if it was created (True) or updated (False).
        """
        active_project = await self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to create a blueprint prompt.")

        existing_prompt = await self.prompt_repo.find_project_blueprint_prompt(project_id=active_project.id)

        content = await self._generate_blueprint_content(path)
        name = f"Blueprint: {active_project.name}"

        if existing_prompt:
            update_data = PromptUpdate(name=name, content=content, source_path=path)
            updated_prompt = await self.update_prompt(prompt_id=existing_prompt.id, prompt_in=update_data)
            return updated_prompt, False
        else:
            create_data = PromptInternalCreate(
                name=name,
                content=content,
                type=PromptType.BLUEPRINT,
                source_path=path,
                project_id=active_project.id,
            )
            new_prompt = await self.prompt_repo.create(obj_in=create_data)
            return new_prompt, True

    async def get_project_blueprint_prompt(self) -> Prompt | None:
        """Retrieves the blueprint prompt for the currently active project."""
        active_project = await self.project_service.project_repo.get_active()
        if not active_project:
            return None
        return await self.prompt_repo.find_project_blueprint_prompt(project_id=active_project.id)

    async def delete_project_blueprint_prompt(self) -> None:
        """Finds and deletes the blueprint prompt for the currently active project."""
        active_project = await self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to delete a blueprint prompt.")

        existing_prompt = await self.prompt_repo.find_project_blueprint_prompt(project_id=active_project.id)
        if existing_prompt:
            await self.delete_prompt(prompt_id=existing_prompt.id)
        else:
            raise PromptNotFoundException("Blueprint prompt not found for the active project.")

    async def toggle_active_attachment_for_current_project(self, prompt_id: int) -> tuple[Prompt, bool]:
        """Toggles the attachment of a prompt to the currently active project."""
        active_project = await self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to attach or detach prompts.")

        prompt = await self.get_prompt(prompt_id)

        attachment = await self.prompt_repo.find_attachment(prompt_id=prompt_id, project_id=active_project.id)

        if attachment:
            await self.prompt_repo.detach_from_project(attachment)
        else:
            await self.prompt_repo.attach_to_project(prompt_id=prompt_id, project_id=active_project.id)

        return prompt, not bool(attachment)


class PromptPageService:
    def __init__(
        self,
        prompt_service: PromptService,
        project_service: ProjectService,
        blueprint_service: BlueprintService,
    ):
        self.prompt_service = prompt_service
        self.project_service = project_service
        self.blueprint_service = blueprint_service

    @staticmethod
    async def get_new_global_prompt_form_context() -> dict:
        return {"prompt_type": PromptType.GLOBAL}

    async def get_new_project_prompt_form_context(self) -> dict:
        active_project = await self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to create a project prompt.")
        return {"prompt_type": PromptType.PROJECT}

    async def get_edit_global_prompt_form_context(self, prompt_id: int) -> dict:
        prompt = await self.prompt_service.get_prompt(prompt_id=prompt_id)
        return {"prompt": prompt}

    async def get_edit_project_prompt_form_context(self, prompt_id: int) -> dict:
        prompt = await self.prompt_service.get_prompt(prompt_id=prompt_id)
        return {"prompt": prompt}

    async def get_prompt_view_context(self, prompt_id: int) -> dict:
        prompt = await self.prompt_service.get_prompt(prompt_id=prompt_id)
        active_project = await self.project_service.project_repo.get_active()
        attached_prompt_ids = await self._get_attached_prompt_ids(active_project)
        is_attached = prompt.id in attached_prompt_ids
        return {"prompt": prompt, "is_attached": is_attached}

    async def _get_attached_prompt_ids(self, active_project: Project | None) -> set[int]:
        if not active_project:
            return set()
        return {
            attachment.prompt_id
            for attachment in await self.prompt_service.prompt_repo.get_project_attachments(project_id=active_project.id)
        }

    async def get_global_prompts_list_data(self) -> dict:
        active_project = await self.project_service.project_repo.get_active()
        prompts = await self.prompt_service.get_global_prompts()
        attached_prompt_ids = await self._get_attached_prompt_ids(active_project)
        return {
            "prompts": prompts,
            "attached_prompt_ids": attached_prompt_ids,
            "prompt_type": PromptType.GLOBAL,
            "active_project": active_project,
        }

    async def get_project_prompts_list_data(self) -> dict:
        active_project = await self.project_service.project_repo.get_active()
        prompts = await self.prompt_service.get_project_prompts(project=active_project)
        attached_prompt_ids = await self._get_attached_prompt_ids(active_project)
        return {
            "prompts": prompts,
            "attached_prompt_ids": attached_prompt_ids,
            "prompt_type": PromptType.PROJECT,
            "active_project": active_project,
        }

    async def get_blueprint_prompts_list_data(self) -> dict:
        blueprints = await self.blueprint_service.list_blueprints()
        current_prompt = await self.prompt_service.get_project_blueprint_prompt()
        return {"blueprints": blueprints, "prompt": current_prompt}
