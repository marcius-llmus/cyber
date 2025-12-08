from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.enums import LogLevel

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    DATABASE_URL: str = "sqlite+aiosqlite:///workspace/database.db"
    PROJECTS_ROOT_DIR: str = "workspace/projects"
    BLUEPRINTS_ROOT_DIR: str = "workspace/blueprints"
    LOG_LEVEL: LogLevel = LogLevel.INFO
    OBSERVABILITY_ENABLED: bool = False

    @property
    def queries_dir(self) -> str:
        return str(BASE_DIR / "app/context/repomap/queries")

    @field_validator("PROJECTS_ROOT_DIR", "BLUEPRINTS_ROOT_DIR")
    def make_absolute(cls, v: str) -> str: # noqa
        if not Path(v).is_absolute():
            return str(BASE_DIR / v)
        return v

settings = Settings()