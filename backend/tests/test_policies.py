import uuid

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models import Organization, User


def _auth_headers(client, db):
    org = Organization(id=uuid.uuid4(), name="Test Org")
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role="admin",
    )
    db.add(user)
    db.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, org


def _create_bot(client, headers):
    resp = client.post(
        "/api/v1/chatbots", headers=headers, json={"name": "Bot"}
    )
    return resp.json()["id"]


def test_create_policy(client: TestClient, db):
    headers, _ = _auth_headers(client, db)
    bot_id = _create_bot(client, headers)

    response = client.post(
        f"/api/v1/chatbots/{bot_id}/policies",
        headers=headers,
        json={
            "name": "Allow All",
            "policy_type": "security",
            "rules": {"allow": ["*"]},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Allow All"
    assert data["policy_type"] == "security"
    assert data["chatbot_id"] == bot_id


def test_list_policies(client: TestClient, db):
    headers, _ = _auth_headers(client, db)
    bot_id = _create_bot(client, headers)

    client.post(
        f"/api/v1/chatbots/{bot_id}/policies",
        headers=headers,
        json={"name": "P1", "policy_type": "security"},
    )
    client.post(
        f"/api/v1/chatbots/{bot_id}/policies",
        headers=headers,
        json={"name": "P2", "policy_type": "response"},
    )

    response = client.get(
        f"/api/v1/chatbots/{bot_id}/policies", headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_org_level_policy(client: TestClient, db):
    headers, _ = _auth_headers(client, db)

    response = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "name": "Org Policy",
            "policy_type": "security",
            "rules": {},
        },
    )
    assert response.status_code == 201
    assert response.json()["chatbot_id"] is None
