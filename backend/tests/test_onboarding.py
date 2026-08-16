import uuid

import pyotp
from fastapi.testclient import TestClient

from app.core.security import encrypt_totp_secret, hash_password
from app.models import AnalyticsEvent, ChatSession, Chatbot, KnowledgeSource, Organization, User

TOTP_SECRET = "JBSWY3DPEHPK3PXP"


def _seed_org(db, name="Test Org"):
    org = Organization(id=uuid.uuid4(), name=name)
    db.add(org)
    db.commit()
    return org


def _seed_user(db, org, email="admin@test.com", role="admin"):
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role=role,
        full_name="Admin",
    )
    db.add(user)
    db.commit()
    return user


def _auth_header(client, email="admin@test.com", password="testpass123"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _platform_admin_headers(client, email="platform@x.com"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "pw"})
    mfa_token = resp.json()["mfa_token"]
    resp = client.post(
        "/api/v1/auth/mfa/verify-login",
        json={"mfa_token": mfa_token, "code": pyotp.TOTP(TOTP_SECRET).now()},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_onboarding_checklist_empty(client: TestClient, db):
    org = _seed_org(db)
    _seed_user(db, org)
    headers = _auth_header(client)

    resp = client.get("/api/v1/analytics/onboarding", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed_count"] == 0
    assert {s["step"] for s in data["steps"]} == {
        "create_chatbot",
        "add_knowledge_source",
        "test_widget",
        "invite_teammate",
    }
    assert all(s["completed"] is False for s in data["steps"])


def test_onboarding_checklist_records_events_once(client: TestClient, db):
    org = _seed_org(db)
    user = _seed_user(db, org)
    teammate = _seed_user(db, org, email="teammate@test.com")
    bot = Chatbot(id=uuid.uuid4(), organization_id=org.id, name="Support Bot", behaviour="support")
    db.add(bot)
    db.add(KnowledgeSource(id=uuid.uuid4(), organization_id=org.id, chatbot_id=bot.id,
                           source_type="url", uri="https://example.com", sync_status="pending"))
    db.add(ChatSession(id=uuid.uuid4(), organization_id=org.id, chatbot_id=bot.id))
    db.commit()

    headers = _auth_header(client)
    resp = client.get("/api/v1/analytics/onboarding", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed_count"] == 4
    assert all(s["completed"] for s in data["steps"])

    events = db.query(AnalyticsEvent).filter(AnalyticsEvent.event_type == "onboarding.step").all()
    assert {e.payload["step"] for e in events} == {
        "create_chatbot",
        "add_knowledge_source",
        "test_widget",
        "invite_teammate",
    }

    # second call must not duplicate events
    client.get("/api/v1/analytics/onboarding", headers=headers)
    assert db.query(AnalyticsEvent).filter(AnalyticsEvent.event_type == "onboarding.step").count() == 4


def test_feedback_submission(client: TestClient, db):
    org = _seed_org(db)
    user = _seed_user(db, org)
    bot = Chatbot(id=uuid.uuid4(), organization_id=org.id, name="Support Bot", behaviour="support")
    db.add(bot)
    db.commit()

    headers = _auth_header(client)
    resp = client.post(
        "/api/v1/analytics/feedback",
        json={"rating": "down", "message": "confusing answers", "context": "chatbot_test",
              "chatbot_id": str(bot.id)},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "tracked"

    event = db.query(AnalyticsEvent).filter(AnalyticsEvent.event_type == "feedback").first()
    assert event is not None
    assert event.organization_id == org.id
    assert event.chatbot_id == bot.id
    assert event.payload["rating"] == "down"
    assert event.payload["message"] == "confusing answers"
    assert event.payload["context"] == "chatbot_test"


def test_feedback_validation_rating(client: TestClient, db):
    org = _seed_org(db)
    _seed_user(db, org)
    headers = _auth_header(client)
    resp = client.post(
        "/api/v1/analytics/feedback",
        json={"rating": "meh"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_onboarding_funnel_requires_platform_admin(client: TestClient, db):
    org = _seed_org(db)
    _seed_user(db, org, role="admin")
    headers = _auth_header(client)
    resp = client.get("/api/v1/admin/onboarding/funnel", headers=headers)
    assert resp.status_code == 403


def test_onboarding_funnel_cross_org_summary(client: TestClient, db):
    org_a = _seed_org(db, name="Org A")
    _seed_user(db, org_a, email="a@test.com")
    _seed_user(db, org_a, email="a2@test.com")
    bot_a = Chatbot(id=uuid.uuid4(), organization_id=org_a.id, name="Bot A", behaviour="support")
    db.add(bot_a)
    db.add(ChatSession(id=uuid.uuid4(), organization_id=org_a.id, chatbot_id=bot_a.id))
    db.commit()

    org_b = _seed_org(db, name="Org B")
    _seed_user(db, org_b, email="b@test.com")
    db.commit()

    # platform admin login (MFA enabled)
    pa_org = _seed_org(db, name="Admin Org")
    pa = User(
        id=uuid.uuid4(), email="platform@x.com",
        hashed_password=hash_password("pw"), organization_id=pa_org.id,
        role="platform_admin", mfa_enabled=True,
        totp_secret=encrypt_totp_secret(TOTP_SECRET),
    )
    db.add(pa)
    db.commit()
    headers = _platform_admin_headers(client)

    # record onboarding.step for org_a so it appears in the funnel
    client.post(
        "/api/v1/analytics/feedback",
        json={"rating": "up", "context": "chatbot_test", "chatbot_id": str(bot_a.id)},
        headers=_auth_header(client, email="a@test.com"),
    )

    resp = client.get("/api/v1/admin/onboarding/funnel", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_organizations"] == 3  # org_a + org_b + admin org
    assert data["summary"]["with_chatbot"] == 1
    assert data["summary"]["with_teammate"] == 1
    assert data["summary"]["feedback_up"] == 1

    row_a = next(r for r in data["funnel"] if r["name"] == "Org A")
    assert row_a["has_chatbot"] is True
    assert row_a["has_widget_session"] is True
    assert row_a["has_teammate"] is True
    assert row_a["has_knowledge_source"] is False

    fb = next(f for f in data["feedback"] if f["org_name"] == "Org A")
    assert fb["rating"] == "up"
    assert fb["context"] == "chatbot_test"