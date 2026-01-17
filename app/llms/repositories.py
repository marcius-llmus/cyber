from sqlalchemy import select, update

from app.commons.repositories import BaseRepository
from app.llms.enums import LLMProvider, LLMRole
from app.llms.models import LLMSettings


class LLMSettingsRepository(BaseRepository[LLMSettings]):
    model = LLMSettings

    async def get_by_model_name(self, model_name: str) -> LLMSettings | None:
        result = await self.db.execute(select(LLMSettings).filter_by(model_name=model_name))
        return result.scalars().first()

    async def get_all(self) -> list[LLMSettings]:
        result = await self.db.execute(select(self.model))
        return list(result.scalars().all())

    async def update_api_key_for_provider(self, provider: LLMProvider, api_key: str | None) -> None:
        await self.db.execute(
            update(self.model)
            .where(self.model.provider == provider)
            .values(api_key=api_key)
        )
        await self.db.flush()

    async def get_api_key_for_provider(self, provider: LLMProvider) -> str | None:
        llm_setting_with_key = (
            await self.db.execute(
                select(LLMSettings).filter(LLMSettings.provider == provider, LLMSettings.api_key.isnot(None)).limit(1)
            )
        )
        if settings := llm_setting_with_key.scalars().first():
            return settings.api_key
        return None

    async def get_by_role(self, role: LLMRole) -> LLMSettings | None:
        result = await self.db.execute(select(self.model).filter_by(active_role=role))
        return result.scalars().one_or_none()

    async def set_active_role(self, llm_id: int, role: LLMRole) -> None:
        # clear role for any other LLM
        await self.db.execute(
            update(self.model)
            .where(self.model.active_role == role)
            .values(active_role=None)
        )
        # set role for the target LLM
        await self.db.execute(
            update(self.model).where(self.model.id == llm_id).values(active_role=role)
        )
        await self.db.flush()
