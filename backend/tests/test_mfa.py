import uuid

import pyotp
from fastapi.testclient import TestClient

from app.core.security import decrypt_totp_secret, hash_password, verify_recovery_code
from app.models import Organization, User


def _seed_user(client: TestClient, db, role="admin", email="admin@test.com", mfa_enabled=False):
    org = Organization(id=uuid.uuid4(), name="Test Org")
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role=role,
        full_name="Admin",
        mfa_enabled=mfa_enabled,
    )
    db.add(user)
    db.commit()
    return org, user


def _login(client, email="admin@test.com", password="testpass123"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def _setup_and_enable(client, db, user, secret, token):
    resp = client.post(
        "/api/v1/auth/mfa/enable",
        json={"secret": secret, "code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    db.refresh(user)
    return resp.json()


def test_mfa_status_default_disabled(client: TestClient, db):
    _seed_user(client, db)
    token = _login(client).json()["access_token"]
    resp = client.get("/api/v1/auth/mfa/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"mfa_enabled": False}


def test_mfa_setup_wrong_password(client: TestClient, db):
    _seed_user(client, db)
    token = _login(client).json()["access_token"]
    resp = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "wrongpass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_mfa_setup_returns_secret_and_qr(client: TestClient, db):
    _seed_user(client, db)
    token = _login(client).json()["access_token"]
    resp = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["secret"]
    assert data["provisioning_uri"].startswith("otpauth://totp/")
    assert "Scout.io" in data["provisioning_uri"]
    assert data["qr_data_uri"].startswith("data:image/png;base64,")


def test_mfa_enable_persists_encrypted_secret_and_hashed_codes(client: TestClient, db):
    org, user = _seed_user(client, db)
    token = _login(client).json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    secret = setup["secret"]

    data = _setup_and_enable(client, db, user, secret, token)

    assert user.mfa_enabled is True
    assert user.totp_secret != secret
    assert decrypt_totp_secret(user.totp_secret) == secret
    assert len(data["recovery_codes"]) == 10
    for code in data["recovery_codes"]:
        assert code not in user.recovery_codes


def test_mfa_enable_wrong_code(client: TestClient, db):
    org, user = _seed_user(client, db)
    token = _login(client).json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    resp = client.post(
        "/api/v1/auth/mfa/enable",
        json={"secret": setup["secret"], "code": "000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert user.mfa_enabled is False


def test_mfa_login_returns_verify_step(client: TestClient, db):
    org, user = _seed_user(client, db)
    token = _login(client).json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    _setup_and_enable(client, db, user, setup["secret"], token)

    resp = _login(client)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mfa_required"] is True
    assert data["mfa_token"]
    assert "access_token" not in data
    assert "refresh_token" not in data


def test_mfa_verify_login_with_totp(client: TestClient, db):
    org, user = _seed_user(client, db)
    token = _login(client).json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    _setup_and_enable(client, db, user, setup["secret"], token)

    mfa_token = _login(client).json()["mfa_token"]
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": pyotp.TOTP(setup["secret"]).now()},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


def test_mfa_verify_login_wrong_code(client: TestClient, db):
    org, user = _seed_user(client, db)
    token = _login(client).json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    _setup_and_enable(client, db, user, setup["secret"], token)

    mfa_token = _login(client).json()["mfa_token"]
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": "000000"},
    )
    assert resp.status_code == 401


def test_mfa_verify_login_rejects_access_token_as_mfa_token(client: TestClient, db):
    org, user = _seed_user(client, db)
    access_token = _login(client).json()["access_token"]
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": access_token, "code": "123456"},
    )
    assert resp.status_code == 401


def test_mfa_recovery_code_login_single_use(client: TestClient, db):
    org, user = _seed_user(client, db)
    token = _login(client).json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    data = _setup_and_enable(client, db, user, setup["secret"], token)
    recovery_code = data["recovery_codes"][0]

    mfa_token = _login(client).json()["mfa_token"]
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": recovery_code},
    )
    assert resp.status_code == 200
    db.refresh(user)
    remaining = user.recovery_codes
    assert len(remaining) == 9

    mfa_token2 = _login(client).json()["mfa_token"]
    resp2 = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token2, "code": recovery_code},
    )
    assert resp2.status_code == 401


def test_mfa_disable_requires_password_and_code(client: TestClient, db):
    org, user = _seed_user(client, db)
    token = _login(client).json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    _setup_and_enable(client, db, user, setup["secret"], token)

    resp = client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": "wrongpass", "code": pyotp.TOTP(setup["secret"]).now()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401

    resp = client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": "testpass123", "code": "000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401

    resp = client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": "testpass123", "code": pyotp.TOTP(setup["secret"]).now()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204
    db.refresh(user)
    assert user.mfa_enabled is False
    assert user.totp_secret is None
    assert user.recovery_codes is None


def test_mfa_regenerate_recovery_codes(client: TestClient, db):
    org, user = _seed_user(client, db)
    token = _login(client).json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    data = _setup_and_enable(client, db, user, setup["secret"], token)
    old_code = data["recovery_codes"][0]

    resp = client.post(
        "/api/v1/auth/mfa/recovery-codes/regenerate",
        json={"password": "testpass123", "code": pyotp.TOTP(setup["secret"]).now()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    new_codes = resp.json()["recovery_codes"]
    assert len(new_codes) == 10
    assert old_code not in new_codes

    # old code must no longer work
    db.refresh(user)
    assert verify_recovery_code(old_code, user.recovery_codes) is False
    assert verify_recovery_code(new_codes[0], user.recovery_codes) is True


def test_platform_admin_without_mfa_denied(client: TestClient, db):
    _seed_user(client, db, role="platform_admin", email="platform@x.com")
    token = _login(client, email="platform@x.com").json()["access_token"]
    resp = client.get("/api/v1/admin/organizations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert "MFA" in resp.json()["detail"]


def test_platform_admin_after_mfa_enabled_can_access(client: TestClient, db):
    org, user = _seed_user(client, db, role="platform_admin", email="platform@x.com")
    token = _login(client, email="platform@x.com").json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    _setup_and_enable(client, db, user, setup["secret"], token)

    resp = client.get("/api/v1/admin/organizations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_mfa_flow_after_enable_login_requires_step(client: TestClient, db):
    org, user = _seed_user(client, db)
    token = _login(client).json()["access_token"]
    setup = client.post(
        "/api/v1/auth/mfa/setup",
        json={"password": "testpass123"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    _setup_and_enable(client, db, user, setup["secret"], token)

    mfa_token = _login(client).json()["mfa_token"]
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": pyotp.TOTP(setup["secret"]).now()},
    )
    tokens = resp.json()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@test.com"