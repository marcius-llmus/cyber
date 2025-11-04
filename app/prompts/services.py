from app.projects.models import Project
from app.projects.exceptions import ActiveProjectRequiredException
from app.blueprints.services import BlueprintService
from app.projects.services import ProjectService
from app.prompts.exceptions import (
    PromptNotFoundException,
    UnsupportedPromptTypeException,
)
from app.prompts.repositories import PromptRepository
from app.prompts.schemas import (
    NewPromptFormContext,
    PromptCreate,
    PromptsPageData,
    PromptUpdate,
)
from app.prompts.enums import PromptType
from app.prompts.models import Prompt


class PromptService:
    def __init__(self, prompt_repo: PromptRepository, project_service: ProjectService):
        self.prompt_repo = prompt_repo
        self.project_service = project_service

    def get_prompt(self, prompt_id: int) -> Prompt:
        prompt = self.prompt_repo.get(pk=prompt_id)
        if not prompt:
            raise PromptNotFoundException(f"Prompt with id {prompt_id} not found.")
        return prompt

    def create_global_prompt(self, prompt_in: PromptCreate) -> Prompt:
        """Creates a global prompt."""
        if prompt_in.type != PromptType.GLOBAL:
            raise UnsupportedPromptTypeException("Invalid type for a global prompt.")
        prompt_in.project_id = None  # Ensure project_id is not set for global prompts
        return self.prompt_repo.create(obj_in=prompt_in)

    def create_project_prompt(self, prompt_in: PromptCreate) -> Prompt:
        """Creates a project-specific prompt, ensuring an active project exists."""
        active_project = self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to create a project prompt.")

        if prompt_in.type != PromptType.PROJECT:
            raise UnsupportedPromptTypeException("Invalid type for a project prompt.")

        prompt_in.project_id = active_project.id  # Ensure it's set to the active project
        return self.prompt_repo.create(obj_in=prompt_in)

    def update_prompt(self, prompt_id: int, prompt_in: PromptUpdate) -> Prompt:
        db_obj = self.get_prompt(prompt_id)
        return self.prompt_repo.update(db_obj=db_obj, obj_in=prompt_in)

    def delete_prompt(self, prompt_id: int) -> None:
        self.get_prompt(prompt_id)  # Ensures the prompt exists before attempting deletion
        self.prompt_repo.delete(pk=prompt_id)

    def get_global_prompts(self) -> list[Prompt]:
        return self.prompt_repo.list_global()

    def get_project_prompts(self, project: Project | None) -> list[Prompt]:
        if not project:
            return []
        return self.prompt_repo.list_by_project(project_id=project.id)

    def _generate_blueprint_content(self, path: str) -> str:
        """
        MOCKED: Generates a blueprint from the given path.
        This will be replaced by a call to a dedicated BlueprintService.
        """
        # This is a placeholder. The real implementation would scan the filesystem.
        return f"Blueprint for: {path}\n\n.gitignore\nREADME.md\napp/\n  __init__.py\n  main.py"

    def create_or_update_project_blueprint_prompt(self, path: str) -> tuple[Prompt, bool]:
        """
        Generates a blueprint from a path and creates or updates a special prompt
        for the currently active project.
        Returns the prompt and a boolean indicating if it was created (True) or updated (False).
        """
        active_project = self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to create a blueprint prompt.")

        existing_prompt = self.prompt_repo.find_project_blueprint_prompt(project_id=active_project.id)

        content = self._generate_blueprint_content(path)
        name = f"Blueprint: {active_project.name}"

        if existing_prompt:
            update_data = PromptUpdate(name=name, content=content, source_path=path)
            updated_prompt = self.update_prompt(prompt_id=existing_prompt.id, prompt_in=update_data)
            return updated_prompt, False
        else:
            create_data = PromptCreate(
                name=name, content=content, type=PromptType.BLUEPRINT, project_id=active_project.id, source_path=path
            )
            new_prompt = self.create_prompt(prompt_in=create_data)
            return new_prompt, True

    def delete_project_blueprint_prompt(self) -> None:
        """Finds and deletes the blueprint prompt for the currently active project."""
        active_project = self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to delete a blueprint prompt.")

        existing_prompt = self.prompt_repo.find_project_blueprint_prompt(project_id=active_project.id)
        if existing_prompt:
            self.delete_prompt(prompt_id=existing_prompt.id)
        else:
            raise PromptNotFoundException("Blueprint prompt not found for the active project.")

    def toggle_project_attachment(self, prompt_id: int) -> tuple[Prompt, bool]:
        """Toggles the attachment of a prompt to the currently active project."""
        active_project = self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to attach or detach prompts.")

        prompt = self.get_prompt(prompt_id)

        attachment = self.prompt_repo.find_attachment(prompt_id=prompt_id, project_id=active_project.id)

        if attachment:
            self.prompt_repo.detach_from_project(attachment)
        else:
            self.prompt_repo.attach_to_project(prompt_id=prompt_id, project_id=active_project.id)

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

    def get_prompts_page_data(self) -> PromptsPageData:
        active_project = self.project_service.project_repo.get_active()
        global_prompts = self.prompt_service.get_global_prompts()
        project_prompts = self.prompt_service.get_project_prompts(project=active_project)
        blueprints = self.blueprint_service.list_blueprints()

        attached_prompt_ids = set()
        blueprint_prompt = None
        if active_project:
            blueprint_prompt = self.prompt_service.prompt_repo.find_project_blueprint_prompt(
                project_id=active_project.id
            )
            attached_prompt_ids = {
                attachment.prompt_id
                for attachment in self.prompt_service.prompt_repo.get_project_attachments(project_id=active_project.id)
            }

        return {
            "global_prompts": global_prompts,
            "project_prompts": project_prompts,
            "active_project": active_project,
            "blueprint_prompt": blueprint_prompt,
            "blueprints": blueprints,
            "attached_prompt_ids": attached_prompt_ids,
        }

    @staticmethod
    def get_new_global_prompt_form_context() -> NewPromptFormContext:
        return {"prompt_type": "global"}

    def get_new_project_prompt_form_context(self) -> NewPromptFormContext:
        active_project = self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("An active project is required to create a project prompt.")
        return {
            "prompt_type": "project",
            "project_id": str(active_project.id),
        }

    def get_edit_global_prompt_form_context(self, prompt_id: int) -> dict:
        prompt = self.prompt_service.get_prompt(prompt_id=prompt_id)
        return {"prompt": prompt}

    def get_edit_project_prompt_form_context(self, prompt_id: int) -> dict:
        prompt = self.prompt_service.get_prompt(prompt_id=prompt_id)
        return {"prompt": prompt}

    def _get_attached_prompt_ids(self, active_project: Project | None) -> set[int]:
        if not active_project:
            return set()
        return {
            attachment.prompt_id
            for attachment in self.prompt_service.prompt_repo.get_project_attachments(project_id=active_project.id)
        }

    def get_global_prompts_list_data(self) -> dict:
        active_project = self.project_service.project_repo.get_active()
        prompts = self.prompt_service.get_global_prompts()
        attached_prompt_ids = self._get_attached_prompt_ids(active_project)
        return {"prompts": prompts, "attached_prompt_ids": attached_prompt_ids}

    def get_project_prompts_list_data(self) -> dict:
        active_project = self.project_service.project_repo.get_active()
        prompts = self.prompt_service.get_project_prompts(project=active_project)
        attached_prompt_ids = self._get_attached_prompt_ids(active_project)
        return {"prompts": prompts, "attached_prompt_ids": attached_prompt_ids}