import logging
from app.projects.services import ProjectService


class ContextService:
    def __init__(self, project_service: ProjectService):
        self.project_service = project_service

    async def get_project_file_tree(self) -> dict:
        # This is a placeholder. In a real scenario, this service would
        # scan the active project's directory, respect .gitignore, and
        # build a tree structure.
        active_project = await self.project_service.project_repo.get_active()
        if not active_project:
            return {}

        return {
            "type": "folder",
            "name": active_project.name,
            "path": active_project.path,
            "children": [
                {
                    "type": "folder",
                    "name": "app",
                    "path": f"{active_project.path}/app",
                    "children": [
                        {"type": "file", "name": "main.py", "path": f"{active_project.path}/app/main.py"},
                        {"type": "file", "name": "models.py", "path": f"{active_project.path}/app/models.py"},
                    ],
                },
                {"type": "file", "name": "README.md", "path": f"{active_project.path}/README.md"},
            ],
        }

    async def add_to_active_context(self, file_path: str) -> None:
        """
        Adds a file to the active context (Tier 2).
        """
        # TODO: Implement logic to persist this to the DB or Redis state
        logging.info(f"Adding {file_path} to active context")

    async def remove_from_active_context(self, file_path: str) -> None:
        """
        Removes a file from the active context.
        """
        # TODO: Implement logic to remove from DB or Redis state
        logging.info(f"Removing {file_path} from active context")


class ContextPageService:
    def __init__(self, context_service: ContextService):
        self.context_service = context_service

    async def get_file_tree_page_data(self) -> dict:
        file_tree = await self.context_service.get_project_file_tree()
        return {"file_tree": file_tree}