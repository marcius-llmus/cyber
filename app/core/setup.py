import logging
import os
import shutil
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def initialize_workspace() -> None:
    """
    Ensures the workspace directories exist and are seeded with default examples.
    """
    logger.info("Initializing workspace...")

    # 1. Ensure directories exist
    os.makedirs(settings.PROJECTS_ROOT_DIR, exist_ok=True)
    os.makedirs(settings.BLUEPRINTS_ROOT_DIR, exist_ok=True)

    # 2. Seed Hello World Project
    # Source is relative to the working directory (/app) in the container
    hello_world_src = Path("seeds/projects/hello_world")
    hello_world_dst = Path(settings.PROJECTS_ROOT_DIR) / "hello_world"

    if hello_world_src.exists() and not hello_world_dst.exists():
        logger.info(f"Seeding 'hello_world' project to {hello_world_dst}")
        shutil.copytree(hello_world_src, hello_world_dst)

    # 3. Seed Async Basics Blueprint
    blueprint_src = Path("seeds/blueprints/async_basics")
    blueprint_dst = Path(settings.BLUEPRINTS_ROOT_DIR) / "async_basics"

    if blueprint_src.exists() and not blueprint_dst.exists():
        logger.info(f"Seeding 'async_basics' blueprint to {blueprint_dst}")
        shutil.copytree(blueprint_src, blueprint_dst)
