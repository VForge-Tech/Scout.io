import uuid

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models import Organization, User


def _seed(db, admin_role="admin"):
    org = Organization(id=uuid.uuid4(), name="Test Org")
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role=admin_role,
        full_name="Admin",
    )
    db.add(user)
    db.commit()
    return org, user


def _admin_headers(client, db):
    _seed(db, admin_role="admin")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_organizations(client: TestClient, db):
    headers = _admin_headers(client, db)
    response = client.get("/api/v1/admin/organizations", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_organization(client: TestClient, db):
    headers = _admin_headers(client, db)
    response = client.get("/api/v1/admin/organizations", headers=headers)
    org_id = response.json()[0]["id"]

    response = client.get(
        f"/api/v1/admin/organizations/{org_id}", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Org"


def test_update_organization_status(client: TestClient, db):
    headers = _admin_headers(client, db)
    response = client.get("/api/v1/admin/organizations", headers=headers)
    org_id = response.json()[0]["id"]

    response = client.patch(
        f"/api/v1/admin/organizations/{org_id}",
        headers=headers,
        json={"suspended": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"


def test_platform_stats(client: TestClient, db):
    headers = _admin_headers(client, db)
    response = client.get("/api/v1/admin/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_organizations"] >= 1
    assert data["total_users"] >= 1


def test_non_admin_cannot_access_admin(client: TestClient, db):
    _seed(db, admin_role="member")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/admin/organizations", headers=headers)
    assert response.status_code == 403
