from sqlalchemy.orm import Session
from app.core.db import engine
from contextlib import contextmanager


def get_db():
    """
    FastAPI dependency that provides a transactional database session.
    """
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@contextmanager
def db_session_manager():
    """
    Context manager for a transactional database session, for use in non-request contexts like WebSockets.
    """
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
