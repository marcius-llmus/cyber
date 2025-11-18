from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.commons.repositories import BaseRepository
from app.llms.enums import LLMProvider
from app.settings.models import LLMSettings, Settings
from app.settings.schemas import SettingsCreate


class LLMSettingsRepository(BaseRepository[LLMSettings]):
    model = LLMSettings

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def get_by_model_name(self, model_name: str) -> LLMSettings | None:
        result = await self.db.execute(select(LLMSettings).filter_by(model_name=model_name))
        return result.scalars().first()

    async def update_api_key_for_provider(self, provider: LLMProvider, api_key: str | None) -> None:
        await self.db.execute(
            update(self.model)
            .where(self.model.provider == provider)
            .values(api_key=api_key)
        )
        await self.db.flush()


class SettingsRepository(BaseRepository[Settings]):
    model = Settings

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(self, obj_in: SettingsCreate) -> Settings:
        db_obj = self.model(**obj_in.model_dump(), id=1)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def get(self, pk: int = 1) -> Settings | None:
        return await self.db.get(self.model, pk)

    async def delete(self, *, pk: int = 1) -> Settings | None:
        """Settings is a singleton and cannot be deleted."""
        raise NotImplementedError("Settings is a singleton and cannot be deleted.")
