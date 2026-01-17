from sqlalchemy import select

from app.commons.repositories import BaseRepository
from app.prompts.enums import PromptType
from app.prompts.models import ProjectPromptAttachment, Prompt


class PromptRepository(BaseRepository[Prompt]):
    model = Prompt

    async def list_global(self) -> list[Prompt]:
        stmt = select(self.model).where(self.model.type == PromptType.GLOBAL).order_by(self.model.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_project(self, project_id: int) -> list[Prompt]:
        stmt = (
            select(self.model)
            .where(self.model.project_id == project_id, self.model.type == PromptType.PROJECT)
            .order_by(self.model.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_project_blueprint_prompt(self, project_id: int) -> Prompt | None:
        stmt = select(self.model).where(
            self.model.project_id == project_id,
            self.model.type == PromptType.BLUEPRINT,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def find_attachment(self, prompt_id: int, project_id: int) -> ProjectPromptAttachment | None:
        stmt = select(ProjectPromptAttachment).filter_by(prompt_id=prompt_id, project_id=project_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_project_attachments(self, project_id: int) -> list[ProjectPromptAttachment]:
        stmt = select(ProjectPromptAttachment).filter_by(project_id=project_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_attached_prompts(self, project_id: int) -> list[Prompt]:
        stmt = select(Prompt).join(ProjectPromptAttachment).where(ProjectPromptAttachment.project_id == project_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def attach_to_project(self, prompt_id: int, project_id: int) -> ProjectPromptAttachment:
        attachment = ProjectPromptAttachment(prompt_id=prompt_id, project_id=project_id)
        self.db.add(attachment)
        await self.db.flush()
        return attachment

    async def detach_from_project(self, attachment: ProjectPromptAttachment):
        await self.db.delete(attachment)
        await self.db.flush()
