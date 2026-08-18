import uuid

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models import Organization, User


def _seed_data(client: TestClient, db):
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


def test_login_success(client: TestClient, db):
    _seed_data(client, db)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client: TestClient, db):
    _seed_data(client, db)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient, db):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "testpass123"},
    )
    assert response.status_code == 401


def test_refresh_token(client: TestClient, db):
    _seed_data(client, db)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_invalid_token(client: TestClient, db):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token_here"},
    )
    assert response.status_code == 401


def test_logout(client: TestClient, db):
    _seed_data(client, db)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 204


def test_access_protected_endpoint(client: TestClient, db):
    _seed_data(client, db)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Org"


def test_access_without_token(client: TestClient, db):
    response = client.get("/api/v1/organizations/me")
    assert response.status_code == 401


def test_register_success(client: TestClient, db):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@test.com",
            "password": "testpass123",
            "full_name": "New User",
            "organization_name": "New Org",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

    org = db.query(Organization).filter(Organization.name == "New Org").first()
    assert org is not None
    user = db.query(User).filter(User.email == "new@test.com").first()
    assert user is not None
    assert user.organization_id == org.id
    assert user.role == "admin"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "new@test.com", "password": "testpass123"},
    )
    assert login.status_code == 200


def test_register_duplicate_email(client: TestClient, db):
    _seed_data(client, db)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    assert response.status_code == 409


def test_register_short_password(client: TestClient, db):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@test.com", "password": "123"},
    )
    assert response.status_code == 422
