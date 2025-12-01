from app.commons.repositories import BaseRepository
from app.settings.models import Settings
from app.settings.schemas import SettingsCreate


class SettingsRepository(BaseRepository[Settings]):
    model = Settings

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
