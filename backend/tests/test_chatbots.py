import uuid

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models import Organization, User


def _seed(db):
    org = Organization(id=uuid.uuid4(), name="Test Org")
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role="admin",
        full_name="Admin",
    )
    db.add(user)
    db.commit()
    return org, user


def _auth_header(client, db):
    _seed(db)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_chatbots_empty(client: TestClient, db):
    headers = _auth_header(client, db)
    response = client.get("/api/v1/chatbots", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_create_chatbot(client: TestClient, db):
    headers = _auth_header(client, db)
    response = client.post(
        "/api/v1/chatbots",
        headers=headers,
        json={"name": "My Bot", "description": "Test bot", "behaviour": "creative"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Bot"
    assert data["behaviour"] == "creative"
    assert data["id"] is not None


def test_get_chatbot(client: TestClient, db):
    headers = _auth_header(client, db)
    create_resp = client.post(
        "/api/v1/chatbots",
        headers=headers,
        json={"name": "My Bot"},
    )
    bot_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/chatbots/{bot_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "My Bot"


def test_update_chatbot(client: TestClient, db):
    headers = _auth_header(client, db)
    create_resp = client.post(
        "/api/v1/chatbots",
        headers=headers,
        json={"name": "My Bot"},
    )
    bot_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/chatbots/{bot_id}",
        headers=headers,
        json={"name": "Updated Bot", "behaviour": "strict"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Bot"
    assert response.json()["behaviour"] == "strict"


def test_delete_chatbot(client: TestClient, db):
    headers = _auth_header(client, db)
    create_resp = client.post(
        "/api/v1/chatbots",
        headers=headers,
        json={"name": "My Bot"},
    )
    bot_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/chatbots/{bot_id}", headers=headers)
    assert response.status_code == 204

    response = client.get("/api/v1/chatbots", headers=headers)
    assert response.json() == []


def test_organization_isolation(client: TestClient, db):
    # Create org1 + user1 + bot
    org1 = Organization(id=uuid.uuid4(), name="Org1")
    db.add(org1)
    user1 = User(
        id=uuid.uuid4(),
        email="user1@test.com",
        hashed_password=hash_password("pass"),
        organization_id=org1.id,
    )
    db.add(user1)
    db.commit()

    headers1 = {
        "Authorization": f'Bearer {client.post("/api/v1/auth/login", json={"email": "user1@test.com", "password": "pass"}).json()["access_token"]}'
    }
    client.post(
        "/api/v1/chatbots",
        headers=headers1,
        json={"name": "Org1 Bot"},
    )

    # Create org2 + user2
    org2 = Organization(id=uuid.uuid4(), name="Org2")
    db.add(org2)
    user2 = User(
        id=uuid.uuid4(),
        email="user2@test.com",
        hashed_password=hash_password("pass"),
        organization_id=org2.id,
    )
    db.add(user2)
    db.commit()

    headers2 = {
        "Authorization": f'Bearer {client.post("/api/v1/auth/login", json={"email": "user2@test.com", "password": "pass"}).json()["access_token"]}'
    }

    # org2 should see empty list
    response = client.get("/api/v1/chatbots", headers=headers2)
    assert response.status_code == 200
    assert response.json() == []
