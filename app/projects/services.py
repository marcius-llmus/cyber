import os

import aiofiles.os

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
    async def _get_fs_project_paths() -> set[str]:
        root_dir = settings.PROJECTS_ROOT_DIR
        if not await aiofiles.os.path.isdir(root_dir):
            raise FileNotFoundError(f"Projects root directory not found: {root_dir}")

        paths = set()
        for name in await aiofiles.os.listdir(root_dir):
            full_path = os.path.join(root_dir, name)
            if await aiofiles.os.path.isdir(full_path):
                paths.add(full_path)
        return paths

    async def _synchronize_projects(self) -> None:
        """
        Synchronizes the projects in the database with the directories in PROJECTS_ROOT_DIR.
        """
        fs_project_paths = await self._get_fs_project_paths()

        db_projects = await self.project_repo.list()

        # Ensure strict directory matching by appending separator
        root_prefix = os.path.join(settings.PROJECTS_ROOT_DIR, "")

        db_projects_in_root = {
            p.path: p
            for p in db_projects
            if p.path.startswith(root_prefix)
        }

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
