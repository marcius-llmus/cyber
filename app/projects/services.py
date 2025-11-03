import os

from app.core.config import settings
from app.projects.exceptions import ProjectNotFoundException
from app.projects.models import Project
from app.projects.repositories import ProjectRepository
from app.projects.schemas import ProjectCreate


class ProjectService:
    def __init__(self, project_repo: ProjectRepository):
        self.project_repo = project_repo

    def get_projects(self) -> list[Project]:
        self._synchronize_projects()
        return self.project_repo.list()

    def _synchronize_projects(self) -> None:
        """
        Synchronizes the projects in the database with the directories in PROJECTS_ROOT_DIR.
        """
        root_dir = settings.PROJECTS_ROOT_DIR
        if not os.path.isdir(root_dir):
            os.makedirs(root_dir, exist_ok=True)

        try:
            fs_project_paths = {
                os.path.join(root_dir, name)
                for name in os.listdir(root_dir)
                if os.path.isdir(os.path.join(root_dir, name))
            }
        except FileNotFoundError:
            return

        db_projects_in_root = {p.path: p for p in self.project_repo.list() if p.path.startswith(root_dir)}

        # Add new projects
        for path in fs_project_paths:
            if path not in db_projects_in_root:
                self.project_repo.create(obj_in=ProjectCreate(name=os.path.basename(path), path=path))

        # Remove old projects
        for path, project in db_projects_in_root.items():
            if path not in fs_project_paths:
                self.project_repo.delete(pk=project.id)

    def get_project(self, project_id: int) -> Project:
        project = self.project_repo.get(pk=project_id)
        if not project:
            raise ProjectNotFoundException(f"Project with id {project_id} not found.")
        return project

    def set_active_project(self, project_id: int) -> list[Project]:
        project_to_activate = self.get_project(project_id=project_id)
        current_active = self.project_repo.get_active()

        if current_active and current_active.id != project_to_activate.id:
            current_active.is_active = False
            self.project_repo.db.add(current_active)

        if not project_to_activate.is_active:
            project_to_activate.is_active = True
            self.project_repo.db.add(project_to_activate)

        return self.project_repo.list()


class ProjectPageService:
    def __init__(self, project_service: ProjectService):
        self.project_service = project_service

    def get_projects_page_data(self) -> dict:
        projects = self.project_service.get_projects()
        return {"projects": projects}