"""Tests for Row-Level Security (RLS) enforcement and org isolation.

Note: Full RLS tests require PostgreSQL. These tests verify:
1. Application-level org isolation still works (existing behavior)
2. RLS tests are skipped on SQLite
3. Platform admin bypass logic works at application level
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.session import get_db_for_admin
from app.main import app
from app.models import Chatbot, Message, Organization, Policy, User


# Skip all RLS tests on SQLite since it doesn't support RLS
def is_postgresql(db: Session) -> bool:
    return db.bind.dialect.name == "postgresql"


@pytest.fixture
def two_orgs(db: Session):
    """Create two organizations with users and data."""
    # Org A
    org_a = Organization(id=uuid.uuid4(), name="Org A")
    db.add(org_a)
    user_a = User(
        id=uuid.uuid4(),
        email="usera@orga.com",
        hashed_password=hash_password("pass123"),
        organization_id=org_a.id,
        role="member",
        full_name="User A",
    )
    db.add(user_a)

    chatbot_a = Chatbot(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Chatbot A",
        behaviour="balanced",
    )
    db.add(chatbot_a)

    policy_a = Policy(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        chatbot_id=chatbot_a.id,
        name="Policy A",
        policy_type="source_filter",
        rules={"allowed_source_ids": []},
    )
    db.add(policy_a)

    # Org B
    org_b = Organization(id=uuid.uuid4(), name="Org B")
    db.add(org_b)
    user_b = User(
        id=uuid.uuid4(),
        email="userb@orgb.com",
        hashed_password=hash_password("pass123"),
        organization_id=org_b.id,
        role="member",
        full_name="User B",
    )
    db.add(user_b)

    chatbot_b = Chatbot(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        name="Chatbot B",
        behaviour="balanced",
    )
    db.add(chatbot_b)

    policy_b = Policy(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        chatbot_id=chatbot_b.id,
        name="Policy B",
        policy_type="source_filter",
        rules={"allowed_source_ids": []},
    )
    db.add(policy_b)

    db.commit()

    return {
        "org_a": org_a,
        "user_a": user_a,
        "chatbot_a": chatbot_a,
        "policy_a": policy_a,
        "org_b": org_b,
        "user_b": user_b,
        "chatbot_b": chatbot_b,
        "policy_b": policy_b,
    }


@pytest.fixture
def client_a(two_orgs, client: TestClient):
    """Test client authenticated as user from Org A."""
    token = create_access_token(
        subject=str(two_orgs["user_a"].id),
        organization_id=two_orgs["org_a"].id,
        extra_claims={"role": "member"},
    )
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def client_b(two_orgs, client: TestClient):
    """Test client authenticated as user from Org B."""
    token = create_access_token(
        subject=str(two_orgs["user_b"].id),
        organization_id=two_orgs["org_b"].id,
        extra_claims={"role": "member"},
    )
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def platform_admin_client(two_orgs, db: Session, client: TestClient):
    """Test client authenticated as platform admin."""
    admin_org = Organization(id=uuid.uuid4(), name="Admin Org")
    db.add(admin_org)
    admin_user = User(
        id=uuid.uuid4(),
        email="admin@platform.com",
        hashed_password=hash_password("admin123"),
        organization_id=admin_org.id,
        role="platform_admin",
        full_name="Platform Admin",
        mfa_enabled=True,
    )
    db.add(admin_user)
    db.commit()

    token = create_access_token(
        subject=str(admin_user.id),
        organization_id=admin_org.id,
        extra_claims={"role": "platform_admin"},
    )
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# =============================================================================
# Application-level org isolation tests (work on SQLite)
# =============================================================================

def test_app_level_org_a_cannot_read_org_b_chatbots(client_a, two_orgs):
    """Org A user cannot read Org B's chatbots via API (app-level filtering)."""
    response = client_a.get("/api/v1/chatbots")
    assert response.status_code == 200
    chatbots = response.json()
    assert len(chatbots) == 1
    assert chatbots[0]["name"] == "Chatbot A"

    # Try to directly access Org B's chatbot by ID - should 404
    response = client_a.get(
        f"/api/v1/chatbots/{two_orgs['chatbot_b'].id}"
    )
    assert response.status_code == 404


def test_app_level_org_a_cannot_read_org_b_policies(client_a, two_orgs):
    """Org A user cannot read Org B's policies via API."""
    response = client_a.get(
        f"/api/v1/chatbots/{two_orgs['chatbot_b'].id}/policies"
    )
    assert response.status_code == 404  # Chatbot not found due to app-level filtering


def test_app_level_org_b_cannot_read_org_a_data(client_b, two_orgs):
    """Org B user cannot read Org A's data via API."""
    response = client_b.get("/api/v1/chatbots")
    assert response.status_code == 200
    chatbots = response.json()
    assert len(chatbots) == 1
    assert chatbots[0]["name"] == "Chatbot B"


def test_app_level_platform_admin_can_read_all_organizations(platform_admin_client, two_orgs):
    """Platform admin can read all organizations via admin endpoints."""
    response = platform_admin_client.get("/api/v1/admin/organizations")
    assert response.status_code == 200
    orgs = response.json()
    # Should see both test orgs plus admin org
    assert len(orgs) >= 2
    org_names = {o["name"] for o in orgs}
    assert "Org A" in org_names
    assert "Org B" in org_names


def test_app_level_platform_admin_can_read_any_org(platform_admin_client, two_orgs):
    """Platform admin can access any specific org's data."""
    response = platform_admin_client.get(f"/api/v1/admin/organizations/{two_orgs['org_a'].id}")
    assert response.status_code == 200
    org = response.json()
    assert org["name"] == "Org A"

    response = platform_admin_client.get(f"/api/v1/admin/organizations/{two_orgs['org_b'].id}")
    assert response.status_code == 200
    org = response.json()
    assert org["name"] == "Org B"


def test_app_level_regular_admin_cannot_access_platform_admin_endpoints(two_orgs, db: Session, client: TestClient):
    """Regular org admin (not platform_admin) cannot access platform admin endpoints."""
    # Create a regular admin user in Org A
    admin_user = User(
        id=uuid.uuid4(),
        email="admina@orga.com",
        hashed_password=hash_password("admin123"),
        organization_id=two_orgs["org_a"].id,
        role="admin",
        full_name="Org A Admin",
    )
    db.add(admin_user)
    db.commit()

    token = create_access_token(
        subject=str(admin_user.id),
        organization_id=two_orgs["org_a"].id,
        extra_claims={"role": "admin"},
    )
    client.headers.update({"Authorization": f"Bearer {token}"})

    # Should not be able to access admin endpoints requiring platform_admin
    response = client.get("/api/v1/admin/organizations")
    assert response.status_code == 403  # Forbidden - not platform_admin


# =============================================================================
# RLS-specific tests (only run on PostgreSQL)
# =============================================================================

def test_rls_org_a_cannot_read_org_b_users_directly(two_orgs, db: Session):
    """Direct DB query with Org A context cannot see Org B users (PostgreSQL only)."""
    if not is_postgresql(db):
        pytest.skip("Requires PostgreSQL")

    # Set org context to Org A
    db.execute(text("SET LOCAL app.current_org_id = :oid"), {"oid": str(two_orgs["org_a"].id)})

    # Query should only return Org A users
    users = db.query(User).all()
    assert len(users) == 1
    assert users[0].email == "usera@orga.com"


def test_rls_messages_isolated_by_session(two_orgs, db: Session):
    """Messages are isolated via session organization (PostgreSQL only)."""
    if not is_postgresql(db):
        pytest.skip("Requires PostgreSQL")

    from app.models import ChatSession

    session_a = ChatSession(
        id=uuid.uuid4(),
        organization_id=two_orgs["org_a"].id,
        chatbot_id=two_orgs["chatbot_a"].id,
    )
    session_b = ChatSession(
        id=uuid.uuid4(),
        organization_id=two_orgs["org_b"].id,
        chatbot_id=two_orgs["chatbot_b"].id,
    )
    db.add_all([session_a, session_b])
    db.commit()

    msg_a = Message(
        id=uuid.uuid4(),
        session_id=session_a.id,
        role="user",
        content="Message from Org A",
    )
    msg_b = Message(
        id=uuid.uuid4(),
        session_id=session_b.id,
        role="user",
        content="Message from Org B",
    )
    db.add_all([msg_a, msg_b])
    db.commit()

    # Set org context to Org A
    db.execute(text("SET LOCAL app.current_org_id = :oid"), {"oid": str(two_orgs["org_a"].id)})

    # Should only see messages from Org A's sessions
    messages = db.query(Message).all()
    assert len(messages) == 1
    assert messages[0].content == "Message from Org A"

    # Set org context to Org B
    db.execute(text("SET LOCAL app.current_org_id = :oid"), {"oid": str(two_orgs["org_b"].id)})

    messages = db.query(Message).all()
    assert len(messages) == 1
    assert messages[0].content == "Message from Org B"


def test_rls_platform_admin_can_query_all_users(two_orgs, db: Session):
    """Platform admin bypass can query all users when using admin DB session (PostgreSQL only)."""
    if not is_postgresql(db):
        pytest.skip("Requires PostgreSQL")

    for admin_db in get_db_for_admin():
        users = admin_db.query(User).all()
        assert len(users) >= 2
        emails = {u.email for u in users}
        assert "usera@orga.com" in emails
        assert "userb@orgb.com" in emails
        break


def test_rls_platform_admin_can_query_all_chatbots(two_orgs, db: Session):
    """Platform admin bypass can query all chatbots when using admin DB session (PostgreSQL only)."""
    if not is_postgresql(db):
        pytest.skip("Requires PostgreSQL")

    for admin_db in get_db_for_admin():
        chatbots = admin_db.query(Chatbot).all()
        assert len(chatbots) >= 2
        names = {c.name for c in chatbots}
        assert "Chatbot A" in names
        assert "Chatbot B" in names
        break


def test_rls_without_org_context_returns_empty(two_orgs, db: Session):
    """Query without setting org context should return empty (RLS default deny, PostgreSQL only)."""
    if not is_postgresql(db):
        pytest.skip("Requires PostgreSQL")

    # Don't set org context
    users = db.query(User).all()
    assert len(users) == 0


def test_rls_cross_org_insert_blocked(two_orgs, db: Session):
    """Insert with wrong org_id should be blocked by RLS WITH CHECK (PostgreSQL only)."""
    if not is_postgresql(db):
        pytest.skip("Requires PostgreSQL")

    db.execute(text("SET LOCAL app.current_org_id = :oid"), {"oid": str(two_orgs["org_a"].id)})

    fake_chatbot = Chatbot(
        id=uuid.uuid4(),
        organization_id=two_orgs["org_b"].id,
        name="Malicious Chatbot",
        behaviour="balanced",
    )
    db.add(fake_chatbot)

    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_rls_cross_org_update_blocked(two_orgs, db: Session):
    """Update on another org's row should be blocked by RLS (PostgreSQL only)."""
    if not is_postgresql(db):
        pytest.skip("Requires PostgreSQL")

    db.execute(text("SET LOCAL app.current_org_id = :oid"), {"oid": str(two_orgs["org_a"].id)})

    result = db.query(Chatbot).filter(Chatbot.id == two_orgs["chatbot_b"].id).first()
    assert result is None


def test_rls_cross_org_delete_blocked(two_orgs, db: Session):
    """Delete on another org's row should be blocked by RLS (PostgreSQL only)."""
    if not is_postgresql(db):
        pytest.skip("Requires PostgreSQL")

    db.execute(text("SET LOCAL app.current_org_id = :oid"), {"oid": str(two_orgs["org_a"].id)})

    result = db.query(Chatbot).filter(Chatbot.id == two_orgs["chatbot_b"].id).delete()
    assert result == 0


# =============================================================================
# Widget session tests (app-level)
# =============================================================================

def test_widget_session_creates_with_org_context(two_orgs, client: TestClient):
    """Widget session creation includes org context in token."""
    response = client.post(
        "/api/v1/widget/sessions",
        json={"chatbot_id": str(two_orgs["chatbot_a"].id), "customer_id": "test-customer"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "token" in data
    
    # Verify token contains org_id
    from app.core.security import decode_token
    payload = decode_token(data["token"])
    assert payload["type"] == "widget"
    assert payload["org_id"] == str(two_orgs["org_a"].id)
    assert payload["chatbot_id"] == str(two_orgs["chatbot_a"].id)