import pytest
from fastapi.testclient import TestClient

from app.core.db import SessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.chatbot import Chatbot

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    """Fixture to clear data before each test."""
    from app.core.db import engine
    from app.models.base import Base

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.query(Chatbot).delete()
        db.commit()
    finally:
        db.close()


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_route_no_token():
    # Attempting to fetch chatbots without authorization header should return 401
    response = client.get("/api/v1/chatbots")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_protected_route_invalid_token():
    # Attempting to query with garbage token should fail validation
    response = client.get(
        "/api/v1/chatbots", headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_protected_route_missing_claim():
    # Missing org_id claim in JWT token payload
    token = create_access_token({"sub": "admin"})
    response = client.get(
        "/api/v1/chatbots", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token does not contain org_id claim"


def test_organization_isolation_flow():
    # 1. Generate access tokens for Org A and Org B
    token_a = create_access_token({"org_id": "org_A", "role": "user"})
    token_b = create_access_token({"org_id": "org_B", "role": "user"})

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. Create chatbot under Org A
    res_a = client.post(
        "/api/v1/chatbots",
        json={"name": "Bot A", "description": "Org A Chatbot"},
        headers=headers_a,
    )
    assert res_a.status_code == 201
    bot_a_id = res_a.json()["id"]

    # 3. Create chatbot under Org B
    res_b = client.post(
        "/api/v1/chatbots",
        json={"name": "Bot B", "description": "Org B Chatbot"},
        headers=headers_b,
    )
    assert res_b.status_code == 201
    bot_b_id = res_b.json()["id"]

    # 4. Query chatbots using Org A's token
    list_a = client.get("/api/v1/chatbots", headers=headers_a)
    assert list_a.status_code == 200
    bots_a = list_a.json()
    # Org A should only see 1 chatbot (Bot A)
    assert len(bots_a) == 1
    assert bots_a[0]["name"] == "Bot A"
    assert bots_a[0]["org_id"] == "org_A"

    # 5. Query chatbots using Org B's token
    list_b = client.get("/api/v1/chatbots", headers=headers_b)
    assert list_b.status_code == 200
    bots_b = list_b.json()
    # Org B should only see 1 chatbot (Bot B)
    assert len(bots_b) == 1
    assert bots_b[0]["name"] == "Bot B"
    assert bots_b[0]["org_id"] == "org_B"

    # 6. Try to fetch Bot B using Org A's credentials (should fail with 404)
    get_bot_b_via_a = client.get(f"/api/v1/chatbots/{bot_b_id}", headers=headers_a)
    assert get_bot_b_via_a.status_code == 404

    # 7. Try to delete Bot A using Org B's credentials (should fail with 404)
    del_bot_a_via_b = client.delete(f"/api/v1/chatbots/{bot_a_id}", headers=headers_b)
    assert del_bot_a_via_b.status_code == 404
