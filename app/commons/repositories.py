from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository[ModelType: Base]:
    model: type[ModelType]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, pk: Any) -> ModelType | None:
        return await self.db.get(self.model, pk)

    async def create(self, obj_in: BaseModel) -> ModelType:
        db_obj = self.model(**obj_in.model_dump())
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, *, db_obj: ModelType, obj_in: BaseModel) -> ModelType:
        update_data = obj_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_obj, key, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, *, pk: Any) -> ModelType | None:
        db_obj = await self.db.get(self.model, pk)
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.flush()
        return db_obj
