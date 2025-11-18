import os
import asyncio

from app.core.config import settings
from app.blueprints.schemas import Blueprint


class BlueprintService:
    @staticmethod
    async def list_blueprints() -> list[Blueprint]:
        return await asyncio.to_thread(BlueprintService._list_blueprints_sync)

    @staticmethod
    def _list_blueprints_sync() -> list[Blueprint]:
        root_dir = settings.BLUEPRINTS_ROOT_DIR
        if not os.path.isdir(root_dir):
            os.makedirs(root_dir, exist_ok=True)
            return []

        blueprints = []
        for name in sorted(os.listdir(root_dir)):
            path = os.path.join(root_dir, name)
            if os.path.isdir(path):
                blueprints.append(Blueprint(name=name, path=path.replace(f"{root_dir}/", "")))
        return blueprints