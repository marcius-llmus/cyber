import logging
import os

import aiofiles
import aiofiles.os

from app.blueprints.schemas import Blueprint
from app.context.schemas import FileStatus
from app.context.services.codebase import CodebaseService
from app.core.config import settings

logger = logging.getLogger(__name__)


class BlueprintService:
    def __init__(self, codebase_service: CodebaseService):
        self.codebase_service = codebase_service

    @staticmethod
    async def list_blueprints() -> list[Blueprint]:
        root_dir = settings.BLUEPRINTS_ROOT_DIR
        if not await aiofiles.os.path.isdir(root_dir):
            await aiofiles.os.makedirs(root_dir, exist_ok=True)
            return []

        blueprints = []
        for name in sorted(await aiofiles.os.listdir(root_dir)):
            path = os.path.join(root_dir, name)
            if await aiofiles.os.path.isdir(path):
                # this replace is required to show relative only
                blueprints.append(
                    Blueprint(name=name, path=path.replace(f"{root_dir}/", ""))
                )
        return blueprints

    async def get_blueprint_content(self, path: str) -> str:
        try:
            blueprint_root = await self.codebase_service.validate_directory_path(
                settings.BLUEPRINTS_ROOT_DIR, path
            )

            # we treat the blueprint directory as a "project root" for the CodebaseService.
            blueprint_root_str = str(blueprint_root)
            files = await self.codebase_service.resolve_file_patterns(
                blueprint_root_str, ["."]
            )
            read_results = await self.codebase_service.read_files(
                blueprint_root_str, files
            )
        except Exception as e:
            logger.error(
                f"Error reading blueprint content for path '{path}': {e}", exc_info=True
            )
            raise e

        content_blocks = []
        for result in read_results:
            if result.status == FileStatus.SUCCESS:
                content_blocks.append(
                    f'<file path="{result.file_path}">\n{result.content}\n</file>'
                )

        files_xml = "\n\n".join(content_blocks)
        return (
            "<blueprint_architecture_example>\n"
            "<description>\n"
            "The following files represent the architectural blueprint for this project.\n"
            "Use them as the definitive reference for code style, structure, and patterns.\n"
            "</description>\n"
            "<files>\n"
            f"{files_xml}\n"
            "</files>\n"
            "</blueprint_architecture_example>"
        )
