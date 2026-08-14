from collections.abc import Generator
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db(org_id: UUID | str | None = None) -> Generator:
    db = SessionLocal()
    try:
        if org_id is not None:
            db.execute(text("SET LOCAL app.current_org_id = :org_id"), {"org_id": str(org_id)})
        yield db
    finally:
        db.close()


def get_db_for_admin() -> Generator:
    """Get a DB session with platform admin bypass enabled for cross-org operations."""
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
        yield db
    finally:
        db.close()
