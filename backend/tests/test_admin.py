import uuid

import pyotp
from fastapi.testclient import TestClient

from app.core.security import encrypt_totp_secret, hash_password
from app.models import Organization, User

TOTP_SECRET = "JBSWY3DPEHPK3PXP"


def _seed(db, admin_role="platform_admin"):
    org = Organization(id=uuid.uuid4(), name="Test Org")
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role=admin_role,
        full_name="Admin",
        mfa_enabled=True,
        totp_secret=encrypt_totp_secret(TOTP_SECRET),
    )
    db.add(user)
    db.commit()
    return org, user


def _login_mfa(client, email="admin@test.com", password="testpass123"):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    mfa_token = resp.json()["mfa_token"]
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": pyotp.TOTP(TOTP_SECRET).now()},
    )
    return resp.json()["access_token"]


def _admin_headers(client, db):
    _seed(db, admin_role="platform_admin")
    token = _login_mfa(client)
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
    token = _login_mfa(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/admin/organizations", headers=headers)
    assert response.status_code == 403
