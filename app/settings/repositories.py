from sqlalchemy.orm import Session

from app.commons.repositories import BaseRepository
from app.llms.enums import LLMProvider
from app.settings.models import LLMSettings, Settings
from app.settings.schemas import SettingsCreate


class LLMSettingsRepository(BaseRepository[LLMSettings]):
    model = LLMSettings

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_model_name(self, model_name: str) -> LLMSettings | None:
        return self.db.query(LLMSettings).filter_by(model_name=model_name).first()

    def update_api_key_for_provider(self, provider: LLMProvider, api_key: str | None) -> None:
        (
            self.db.query(self.model)
            .filter(self.model.provider == provider)
            .update({"api_key": api_key}, synchronize_session=False)
        )
        self.db.flush()


class SettingsRepository(BaseRepository[Settings]):
    model = Settings

    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, obj_in: SettingsCreate) -> Settings:
        db_obj = self.model(**obj_in.model_dump(), id=1)
        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def get(self, pk: int = 1) -> Settings | None:
        return self.db.get(self.model, pk)

    def delete(self, *, pk: int = 1) -> Settings | None:
        """Settings is a singleton and cannot be deleted."""
        raise NotImplementedError("Settings is a singleton and cannot be deleted.")
