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
    return {"Authorization": f"Bearer {token}"}


def _create_bot(client, headers):
    resp = client.post(
        "/api/v1/chatbots", headers=headers, json={"name": "Bot"}
    )
    return resp.json()["id"]


def test_create_knowledge_source(client: TestClient, db):
    headers = _auth_headers(client, db)
    bot_id = _create_bot(client, headers)

    response = client.post(
        f"/api/v1/chatbots/{bot_id}/knowledge-sources",
        headers=headers,
        json={
            "source_type": "website",
            "uri": "https://example.com/docs",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_type"] == "website"
    assert data["uri"] == "https://example.com/docs"
    assert data["sync_status"] == "pending"


def test_list_knowledge_sources(client: TestClient, db):
    headers = _auth_headers(client, db)
    bot_id = _create_bot(client, headers)

    client.post(
        f"/api/v1/chatbots/{bot_id}/knowledge-sources",
        headers=headers,
        json={"source_type": "website", "uri": "https://example.com"},
    )
    client.post(
        f"/api/v1/chatbots/{bot_id}/knowledge-sources",
        headers=headers,
        json={"source_type": "pdf", "uri": "s3://bucket/doc.pdf"},
    )

    response = client.get(
        f"/api/v1/chatbots/{bot_id}/knowledge-sources", headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_delete_knowledge_source(client: TestClient, db):
    headers = _auth_headers(client, db)
    bot_id = _create_bot(client, headers)

    create_resp = client.post(
        f"/api/v1/chatbots/{bot_id}/knowledge-sources",
        headers=headers,
        json={"source_type": "website", "uri": "https://example.com"},
    )
    source_id = create_resp.json()["id"]

    response = client.delete(
        f"/api/v1/chatbots/{bot_id}/knowledge-sources/{source_id}",
        headers=headers,
    )
    assert response.status_code == 204
