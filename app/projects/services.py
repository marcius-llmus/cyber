from app.projects.models import Project
import os
import asyncio

from app.core.config import settings
from app.projects.exceptions import ProjectNotFoundException
from app.projects.models import Project
from app.projects.repositories import ProjectRepository
from app.projects.schemas import ProjectCreate


class ProjectService:
    def __init__(self, project_repo: ProjectRepository):
        self.project_repo = project_repo

    async def get_projects(self) -> list[Project]:
        await self._synchronize_projects()
        return await self.project_repo.list()

    @staticmethod
    def _get_fs_project_paths_sync() -> set[str]:
        root_dir = settings.PROJECTS_ROOT_DIR
        if not os.path.isdir(root_dir):
            os.makedirs(root_dir, exist_ok=True)
            return set()

        try:
            return {
                os.path.join(root_dir, name)
                for name in os.listdir(root_dir)
                if os.path.isdir(os.path.join(root_dir, name))
            }
        except FileNotFoundError:
            return set()

    async def _synchronize_projects(self) -> None:  # noqa
        """
        Synchronizes the projects in the database with the directories in PROJECTS_ROOT_DIR.
        """
        fs_project_paths = await asyncio.to_thread(self._get_fs_project_paths_sync)

        db_projects = await self.project_repo.list()
        db_projects_in_root = {p.path: p for p in db_projects if p.path.startswith(settings.PROJECTS_ROOT_DIR)}

        # Add new projects
        for path in fs_project_paths:
            if path not in db_projects_in_root:
                await self.project_repo.create(obj_in=ProjectCreate(name=os.path.basename(path), path=path))

        # Remove old projects
        for path, project in db_projects_in_root.items():
            if path not in fs_project_paths:
                await self.project_repo.delete(pk=project.id)

    async def get_project(self, project_id: int) -> Project:
        project = await self.project_repo.get(pk=project_id)
        if not project:
            raise ProjectNotFoundException(f"Project with id {project_id} not found.")
        return project

    async def set_active_project(self, project_id: int) -> list[Project]:
        project_to_activate = await self.get_project(project_id=project_id)
        current_active = await self.project_repo.get_active()

        if current_active and current_active.id != project_to_activate.id:
            current_active.is_active = False
            await self.project_repo.deactivate(current_active)

        if not project_to_activate.is_active:
            project_to_activate.is_active = True
            await self.project_repo.activate(project_to_activate)

        return await self.project_repo.list()

    async def get_active_project(self) -> Project | None:
        return await self.project_repo.get_active()


class ProjectPageService:
    def __init__(self, project_service: ProjectService):
        self.project_service = project_service

    async def get_projects_page_data(self) -> dict:
        projects = await self.project_service.get_projects()
        return {"projects": projects}