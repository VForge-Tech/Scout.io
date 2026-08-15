from collections.abc import Generator
from unittest.mock import patch

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set required environment variables BEFORE importing app modules
# This allows the secret manager to fall back to env vars when Vault is unavailable
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_scout.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-min-32-chars-long")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("DEPLOYMENT_ENV", "development")
os.environ.setdefault("VAULT_ADDR", "http://localhost:8200")
os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_placeholder")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test-secret-placeholder")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("BILLING_ENABLED", "true")

from app.api.deps import get_db, get_db_admin, get_db_with_org, get_db_for_admin, get_current_user
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db as get_db_base
from app.main import app
from app.models import User

TEST_DATABASE_URL = "sqlite:///./test_scout.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_db_with_org() -> Generator:
    """Override for get_db_with_org - SQLite doesn't support RLS, so just yield db."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_db_admin() -> Generator:
    """Override for get_db_admin - SQLite doesn't support RLS, so just yield db."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user() -> User:
    """Override for get_current_user - return a test user for authenticated endpoints."""
    # This is a minimal mock - tests that need a real user should create one in the test
    # and use the client fixture with manually set headers
    raise pytest.skip("Test requires manual auth setup")


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> Generator:
    # Override database dependencies to use test DB
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_with_org] = override_get_db_with_org
    app.dependency_overrides[get_db_admin] = override_get_db_admin
    app.dependency_overrides[get_db_for_admin] = override_get_db_admin
    
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def org_data():
    return {"name": "Test Organization", "configuration": {"plan": "free"}}


@pytest.fixture
def user_data():
    return {
        "email": "admin@test.com",
        "password": "testpass123",
        "full_name": "Admin User",
        "role": "admin",
    }