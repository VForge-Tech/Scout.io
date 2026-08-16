import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import pyotp

from app.core.security import encrypt_totp_secret, hash_password
from app.domain.offboarding import OffboardingService
from app.models import (
    AnalyticsEvent,
    ApiKey,
    AuditLog,
    ChatSession,
    Chatbot,
    DailyAnalytics,
    KnowledgeSource,
    LLMUsage,
    Message,
    Organization,
    Policy,
    User,
    UsageBillingRecord,
    Webhook,
)

TEST_UPLOAD = Path(__file__).parent / "_offboard_uploads_test"


@pytest.fixture(autouse=True)
def _upload_dir():
    TEST_UPLOAD.mkdir(parents=True, exist_ok=True)
    with patch.dict(os.environ, {"UPLOAD_DIR": str(TEST_UPLOAD)}):
        yield
    import shutil

    shutil.rmtree(TEST_UPLOAD, ignore_errors=True)


@pytest.fixture(autouse=True)
def _no_redis():
    """Fake redis clients in the memory modules so purge ops don't touch a real server."""
    from contextlib import ExitStack

    fake = MagicMock()
    fake.scan.return_value = (0, [])
    fake.delete.return_value = 1
    fake.get.return_value = None
    with ExitStack() as stack:
        for mod in [
            "app.core.memory.session_memory",
            "app.core.memory.org_memory",
            "app.core.memory.knowledge_memory",
            "app.core.memory.optimization_memory",
        ]:
            stack.enter_context(patch(f"{mod}.redis.from_url", return_value=fake))
        yield


def _seed_full_org(db):
    """Create an org with data in every org-scoped table."""
    org = Organization(id=uuid.uuid4(), name="Offboard Org")
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email="owner@offboard.com",
        hashed_password=hash_password("pw"),
        organization_id=org.id,
        role="admin",
    )
    db.add(user)
    bot = Chatbot(id=uuid.uuid4(), organization_id=org.id, name="Bot")
    db.add(bot)
    db.flush()

    session = ChatSession(id=uuid.uuid4(), organization_id=org.id, chatbot_id=bot.id)
    db.add(session)
    db.flush()
    db.add(Message(id=uuid.uuid4(), session_id=session.id, role="user", content="hi"))

    db.add(KnowledgeSource(id=uuid.uuid4(), organization_id=org.id, chatbot_id=bot.id, source_type="api", uri="x"))
    db.add(Policy(id=uuid.uuid4(), organization_id=org.id, chatbot_id=bot.id, name="p", policy_type="source_filter", rules={}))
    db.add(ApiKey(id=uuid.uuid4(), user_id=user.id, organization_id=org.id, name="k", key_prefix="abc", key_hash="h", expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
    db.add(AnalyticsEvent(id=uuid.uuid4(), event_type="msg", organization_id=org.id, chatbot_id=bot.id))
    db.add(DailyAnalytics(id=uuid.uuid4(), date=datetime.now(timezone.utc).date(), organization_id=org.id, chatbot_id=bot.id, entity_type="organization"))
    db.add(LLMUsage(id=uuid.uuid4(), organization_id=org.id, chatbot_id=bot.id, model="m"))
    db.add(UsageBillingRecord(id=uuid.uuid4(), organization_id=org.id, period="2026-08"))
    db.add(Webhook(id=uuid.uuid4(), organization_id=org.id, url="https://x"))
    db.add(AuditLog(id=uuid.uuid4(), user_id=user.id, organization_id=org.id, action="login"))
    db.commit()
    return org, user, session


def _mock_ext(dry=True):
    """Patch Qdrant + Redis + pgvector off so the service runs against mocks."""
    qdrant = MagicMock()
    qdrant.collection_name = "scout_knowledge"
    qdrant.count_organization_chunks.return_value = 3
    qdrant.delete_organization_chunks.return_value = None
    return qdrant


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

def test_execute_purges_all_postgres_rows(db):
    org, user, session = _seed_full_org(db)
    qdrant = _mock_ext()

    svc = OffboardingService(db, qdrant_store=qdrant)
    report = svc.execute(org, admin_id=user.id, ip_address="1.2.3.4")

    # All org-scoped rows gone
    assert report["status"] == "offboarded"
    for model in [
        Message, ChatSession, Chatbot, KnowledgeSource, Policy,
        ApiKey, AnalyticsEvent, DailyAnalytics, LLMUsage, UsageBillingRecord,
        Webhook, User,
    ]:
        assert db.query(model).count() == 0, model.__tablename__

    # Org itself deleted last
    assert db.query(Organization).count() == 0

    # Report reflects per-table deletions
    postgres = report["deleted"]["postgres"]
    for table in ["messages", "sessions", "chatbots", "users", "webhooks"]:
        assert postgres[table] >= 1, table


def test_audit_proof_survives_purge(db):
    org, user, session = _seed_full_org(db)
    qdrant = _mock_ext()
    svc = OffboardingService(db, qdrant_store=qdrant)
    report = svc.execute(org, admin_id=user.id)

    # The proof record is platform-level (org_id/user_id NULL) so it remains.
    proof = db.query(AuditLog).filter(AuditLog.action == "org_offboarded").first()
    assert proof is not None
    assert proof.organization_id is None
    assert proof.user_id is None
    assert proof.details["organization_id"] == str(org.id)
    assert str(proof.id) == report["audit_log_id"]

    # The org-scoped audit log ("login") was purged.
    assert db.query(AuditLog).filter(AuditLog.action == "login").count() == 0


def test_vectors_deleted_from_qdrant(db):
    org, user, session = _seed_full_org(db)
    qdrant = _mock_ext()
    svc = OffboardingService(db, qdrant_store=qdrant)
    report = svc.execute(org, admin_id=user.id)

    qdrant.count_organization_chunks.assert_called_with(str(org.id))
    qdrant.delete_organization_chunks.assert_called_with(str(org.id))
    assert report["deleted"]["qdrant"]["points_deleted"] == 3


def test_redis_caches_purged(db):
    org, user, session = _seed_full_org(db)
    qdrant = _mock_ext()

    with patch("app.domain.offboarding.service.SessionMemory") as sm, \
         patch("app.domain.offboarding.service.OrganizationalMemory") as om, \
         patch("app.domain.offboarding.service.KnowledgeMemory") as km, \
         patch("app.domain.offboarding.service.OptimizationMemory") as opt:
        sm.return_value.purge_org.return_value = 1
        om.return_value.purge_org.return_value = 2
        km.return_value.purge_org.return_value = 0
        opt_inst = MagicMock()
        opt_inst.client.scan.return_value = (0, [])
        opt.return_value = opt_inst

        svc = OffboardingService(db, qdrant_store=qdrant)
        report = svc.execute(org, admin_id=user.id)

        sm.return_value.purge_org.assert_called_once()
        om.return_value.purge_org.assert_called_once_with(str(org.id))
        km.return_value.purge_org.assert_called_once_with(str(org.id))
        opt_inst.invalidate_org_cache.assert_called_once_with(str(org.id))

        redis = report["deleted"]["redis"]
        assert redis["session_history"] == 1
        assert redis["org_config_policies"] == 2


def test_uploads_purged(db):
    org, user, session = _seed_full_org(db)
    # create files under UPLOAD_DIR/<org_id>/<chatbot_id>/
    org_dir = TEST_UPLOAD / str(org.id) / str(session.chatbot_id)
    org_dir.mkdir(parents=True, exist_ok=True)
    (org_dir / "doc.txt").write_text("hello")
    (org_dir / "sub").mkdir(exist_ok=True)
    (org_dir / "sub" / "nested.md").write_text("world")

    qdrant = _mock_ext()
    svc = OffboardingService(db, qdrant_store=qdrant)
    report = svc.execute(org, admin_id=user.id)

    assert report["deleted"]["uploads"]["files"] == 2
    assert not (TEST_UPLOAD / str(org.id)).exists()


def test_preview_counts_without_deleting(db):
    org, user, session = _seed_full_org(db)
    qdrant = _mock_ext()
    svc = OffboardingService(db, qdrant_store=qdrant)

    preview = svc.preview(org)
    assert preview["postgres"]["messages"] >= 1
    assert preview["qdrant"]["points"] == 3
    # Nothing deleted by preview
    assert db.query(Organization).count() == 1
    assert db.query(ChatSession).count() == 1


def test_confirmation_token_roundtrip(db):
    org, user, session = _seed_full_org(db)
    svc = OffboardingService(db, qdrant_store=_mock_ext())

    token = svc.create_confirmation_token(org.id, user.id)
    assert svc.verify_confirmation_token(token, org.id, user.id) is True
    assert svc.verify_confirmation_token(token, uuid.uuid4(), user.id) is False
    assert svc.verify_confirmation_token("garbage", org.id, user.id) is False


# ---------------------------------------------------------------------------
# Endpoint-level tests
# ---------------------------------------------------------------------------

def _admin_headers(client, db):
    org = Organization(id=uuid.uuid4(), name="Admin Org")
    db.add(org)
    admin = User(
        id=uuid.uuid4(), email="platform@x.com",
        hashed_password=hash_password("pw"), organization_id=org.id,
        role="platform_admin", mfa_enabled=True,
        totp_secret=encrypt_totp_secret("JBSWY3DPEHPK3PXP"),
    )
    db.add(admin)
    db.commit()
    resp = client.post("/api/v1/auth/login", json={"email": "platform@x.com", "password": "pw"})
    mfa_token = resp.json()["mfa_token"]
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": pyotp.TOTP("JBSWY3DPEHPK3PXP").now()},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_offboard_endpoint_two_step_flow(client, db):
    org, user, session = _seed_full_org(db)
    org_id = org.id
    headers = _admin_headers(client, db)
    svc = OffboardingService(db, qdrant_store=_mock_ext())

    # Step 1: begin -> preview + token, nothing deleted
    with patch("app.api.endpoints.admin.OffboardingService", return_value=svc):
        r1 = client.post(f"/api/v1/admin/organizations/{org_id}/offboard", headers=headers)
    assert r1.status_code == 200
    body = r1.json()
    assert body["confirmation_token"]
    assert body["postgres"]["messages"] >= 1
    assert db.query(Organization).count() >= 1  # still present

    # Step 2: confirm with token -> purge
    with patch("app.api.endpoints.admin.OffboardingService", return_value=svc):
        r2 = client.post(
            f"/api/v1/admin/organizations/{org_id}/offboard/confirm",
            headers=headers,
            json={"confirmation_token": body["confirmation_token"]},
        )
    assert r2.status_code == 200
    report = r2.json()
    assert report["status"] == "offboarded"
    assert report["deleted"]["postgres"]["users"] >= 1
    assert db.query(Organization).filter(Organization.id == org_id).count() == 0


def test_offboard_confirm_requires_valid_token(client, db):
    org, user, session = _seed_full_org(db)
    headers = _admin_headers(client, db)
    svc = OffboardingService(db, qdrant_store=_mock_ext())

    with patch("app.api.endpoints.admin.OffboardingService", return_value=svc):
        r = client.post(
            f"/api/v1/admin/organizations/{org.id}/offboard/confirm",
            headers=headers,
            json={"confirmation_token": "not-a-real-token"},
        )
    assert r.status_code == 400
    assert db.query(Organization).filter(Organization.id == org.id).count() == 1  # nothing deleted


def test_offboard_requires_platform_admin(client, db):
    org, user, session = _seed_full_org(db)
    # non-admin (member) cannot begin offboarding
    org2 = Organization(id=uuid.uuid4(), name="Member Org")
    db.add(org2)
    member = User(
        id=uuid.uuid4(), email="member@x.com",
        hashed_password=hash_password("pw"), organization_id=org2.id,
        role="member",
    )
    db.add(member)
    db.commit()
    resp = client.post("/api/v1/auth/login", json={"email": "member@x.com", "password": "pw"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(f"/api/v1/admin/organizations/{org.id}/offboard", headers=headers)
    assert r.status_code == 403
