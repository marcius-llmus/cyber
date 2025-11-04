from sqlalchemy import select
from sqlalchemy.orm import Session

from app.commons.repositories import BaseRepository
from app.prompts.models import ProjectPromptAttachment, Prompt
from app.prompts.enums import PromptType


class PromptRepository(BaseRepository[Prompt]):
    model = Prompt

    def __init__(self, db: Session):
        super().__init__(db)

    def list_global(self) -> list[Prompt]:
        stmt = select(self.model).where(self.model.type == PromptType.GLOBAL).order_by(self.model.name)
        return list(self.db.execute(stmt).scalars().all())

    def list_by_project(self, project_id: int) -> list[Prompt]:
        stmt = (
            select(self.model)
            .where(self.model.project_id == project_id, self.model.type == PromptType.PROJECT)
            .order_by(self.model.name)
        )
        return list(self.db.execute(stmt).scalars().all())

    def find_project_blueprint_prompt(self, project_id: int) -> Prompt | None:
        stmt = select(self.model).where(
            self.model.project_id == project_id,
            self.model.type == PromptType.BLUEPRINT,
        )
        return self.db.execute(stmt).scalars().first()

    def find_attachment(self, prompt_id: int, project_id: int) -> ProjectPromptAttachment | None:
        stmt = select(ProjectPromptAttachment).filter_by(prompt_id=prompt_id, project_id=project_id)
        return self.db.execute(stmt).scalars().first()

    def get_project_attachments(self, project_id: int) -> list[ProjectPromptAttachment]:
        stmt = select(ProjectPromptAttachment).filter_by(project_id=project_id)
        return list(self.db.execute(stmt).scalars().all())

    def attach_to_project(self, prompt_id: int, project_id: int) -> ProjectPromptAttachment:
        attachment = ProjectPromptAttachment(prompt_id=prompt_id, project_id=project_id)
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def detach_from_project(self, attachment: ProjectPromptAttachment):
        self.db.delete(attachment)
        self.db.flush()
