from typing import Any

from app.context.schemas import FileTreeNode
from app.context.services.context import WorkspaceService
from app.context.services.filesystem import FileSystemService
from app.projects.services import ProjectService


class ContextPageService:
    """
    Adapts domain data for HTML rendering.
    """
    def __init__(
        self,
        context_service: WorkspaceService,
        fs_service: FileSystemService,
        project_service: ProjectService,
    ):
        self.context_service = context_service
        self.fs_service = fs_service
        self.project_service = project_service

    async def get_file_tree_page_data(self, session_id: int) -> dict:
        project = await self.project_service.get_active_project()
        if not project:
            return {"file_tree": {}}

        # 1. Get Pure Domain Tree
        domain_nodes = await self.fs_service.get_project_file_tree()

        # 2. Get Active Context (to mark selection)
        active_files = await self.context_service.get_active_context(session_id)
        active_paths = {f.file_path for f in active_files}

        # 3. Transform Domain Nodes -> UI Dicts
        ui_tree = self._transform_tree(domain_nodes, active_paths)

        root_node = {
            "type": "folder",
            "name": project.name,
            "path": ".",
            "children": ui_tree,
        }
        return {"file_tree": root_node}

    def _transform_tree(self, nodes: list[FileTreeNode], active_paths: set[str]) -> list[dict[str, Any]]:
        ui_nodes = []
        for node in nodes:
            ui_node: dict[str, Any] = {
                "name": node.name,
                "path": node.path,
                "type": "folder" if node.is_dir else "file",
            }

            if node.is_dir:
                if node.children:
                    ui_node["children"] = self._transform_tree(node.children, active_paths)
            else:
                ui_node["selected"] = node.path in active_paths

            ui_nodes.append(ui_node)
        return ui_nodes

    async def get_context_files_page_data(self, session_id: int) -> dict:
        files = await self.context_service.get_active_context(session_id)
        return {"files": files, "session_id": session_id}
