import sys

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Check if we are running unit tests
is_testing = "pytest" in sys.modules

engine = None

if not is_testing and "postgresql" in settings.DATABASE_URL:
    try:
        # Try connecting to the PostgreSQL container
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        # Verify connection succeeds
        conn = engine.connect()
        conn.close()
    except OperationalError:
        # Fallback to SQLite if PostgreSQL is not running/accessible
        engine = None

if engine is None:
    # In-memory SQLite for testing or fallback
    engine = create_engine(
        "sqlite:///./test.db", connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency to yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
