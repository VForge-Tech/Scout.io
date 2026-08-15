import base64
import hashlib
import hmac
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models import ChatSession, Chatbot, KnowledgeSource, Message, Organization, User

WEBHOOK_SECRET = "test-webhook-secret"


def _make_org_user(db, email="billing@test.com", plan="free", plan_status="active"):
    org = Organization(
        id=uuid.uuid4(),
        name="Billing Org",
        plan=plan,
        plan_status=plan_status,
    )
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role="admin",
    )
    db.add(user)
    db.commit()
    return org, user


def _auth_headers(client, email="billing@test.com"):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _razorpay_sign(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _sub_event(event_type: str, sub_id: str, org_id, plan="growth") -> dict:
    return {
        "event": event_type,
        "payload": {
            "subscription": {
                "entity": {
                    "id": sub_id,
                    "notes": {
                        "organization_id": str(org_id),
                        "plan": plan,
                    },
                }
            }
        },
    }


# --- Checkout session -----------------------------------------------------


def test_checkout_session_creates_subscription(client: TestClient, db, monkeypatch):
    org, user = _make_org_user(db)
    headers = _auth_headers(client)

    captured = {}

    def fake_create_customer(**kwargs):
        captured["customer"] = kwargs
        return {"id": "cust_test_123"}

    def fake_create_subscription(**kwargs):
        captured["subscription"] = kwargs
        return {"id": "sub_test_123", "status": "created", "short_url": "https://rzp.io/test"}

    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.create_customer", fake_create_customer
    )
    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.create_subscription",
        fake_create_subscription,
    )

    resp = client.post(
        "/api/v1/organizations/me/billing/checkout-session",
        headers=headers,
        json={"plan": "growth"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subscription_id"] == "sub_test_123"
    assert data["plan"] == "growth"
    assert data["checkout_url"] == "https://rzp.io/test"
    assert captured["subscription"]["plan_key"] == "growth"
    assert captured["subscription"]["customer_id"] == "cust_test_123"

    db.refresh(org)
    assert org.razorpay_customer_id == "cust_test_123"
    assert org.razorpay_subscription_id == "sub_test_123"


def test_checkout_session_rejects_unknown_plan(client: TestClient, db, monkeypatch):
    _make_org_user(db)
    headers = _auth_headers(client)

    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.create_customer",
        lambda **kw: {"id": "cust_1"},
    )
    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.create_subscription",
        lambda **kw: {"id": "sub_1", "status": "created"},
    )

    resp = client.post(
        "/api/v1/organizations/me/billing/checkout-session",
        headers=headers,
        json={"plan": "nonexistent"},
    )
    assert resp.status_code == 400


def test_checkout_session_rejects_free_plan(client: TestClient, db, monkeypatch):
    _make_org_user(db)
    headers = _auth_headers(client)

    resp = client.post(
        "/api/v1/organizations/me/billing/checkout-session",
        headers=headers,
        json={"plan": "free"},
    )
    assert resp.status_code == 400


# --- Webhook signature ----------------------------------------------------


def test_webhook_rejects_missing_signature(client: TestClient, db, monkeypatch):
    _make_org_user(db)
    payload = json.dumps(_sub_event("subscription.activated", "sub_1", uuid.uuid4())).encode()

    resp = client.post(
        "/api/v1/webhooks/razorpay",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_webhook_rejects_bad_signature(client: TestClient, db, monkeypatch):
    _make_org_user(db)
    payload = json.dumps(_sub_event("subscription.activated", "sub_1", uuid.uuid4())).encode()

    bad_digest = hmac.new(b"wrong", payload, hashlib.sha256).digest()
    resp = client.post(
        "/api/v1/webhooks/razorpay",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": base64.b64encode(bad_digest).decode(),
        },
    )
    assert resp.status_code == 400


# --- Webhook events -------------------------------------------------------


@pytest.mark.parametrize(
    "event_type,expected_status",
    [
        ("subscription.activated", "active"),
        ("subscription.charged", "active"),
        ("subscription.cancelled", "cancelled"),
        ("subscription.halted", "halted"),
    ],
)
def test_webhook_updates_org(
    client: TestClient, db, monkeypatch, event_type, expected_status
):
    org, user = _make_org_user(db, plan="free", plan_status="active")
    payload = json.dumps(
        _sub_event(event_type, "sub_test_x", org.id, plan="growth")
    ).encode()
    signature = _razorpay_sign(payload)

    resp = client.post(
        "/api/v1/webhooks/razorpay",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["event"] == event_type

    db.refresh(org)
    if event_type == "subscription.activated":
        assert org.plan == "growth"
    assert org.plan_status == expected_status


def test_webhook_unknown_event_ignored(client: TestClient, db):
    org, user = _make_org_user(db)
    payload = json.dumps(
        _sub_event("payment.failed", "sub_x", org.id, plan="growth")
    ).encode()
    signature = _razorpay_sign(payload)

    resp = client.post(
        "/api/v1/webhooks/razorpay",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"

    db.refresh(org)
    assert org.plan == "free"


def test_webhook_unknown_org_returns_404(client: TestClient, db):
    payload = json.dumps(
        _sub_event("subscription.activated", "sub_x", uuid.uuid4(), plan="growth")
    ).encode()
    signature = _razorpay_sign(payload)

    resp = client.post(
        "/api/v1/webhooks/razorpay",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
    )
    assert resp.status_code == 404


# --- Plan limit enforcement -----------------------------------------------


def test_chatbot_limit_enforced(client: TestClient, db):
    org, user = _make_org_user(db, plan="free")  # free allows 1 chatbot
    headers = _auth_headers(client)

    first = client.post("/api/v1/chatbots", headers=headers, json={"name": "Bot 1"})
    assert first.status_code == 201

    second = client.post("/api/v1/chatbots", headers=headers, json={"name": "Bot 2"})
    assert second.status_code == 402
    assert "upgrade" in second.json()["detail"].lower()


def test_chatbot_limit_raised_on_growth_plan(client: TestClient, db):
    org, user = _make_org_user(db, plan="growth", plan_status="active")  # allows 10
    headers = _auth_headers(client)

    for i in range(3):
        resp = client.post("/api/v1/chatbots", headers=headers, json={"name": f"Bot {i}"})
        assert resp.status_code == 201


def test_knowledge_source_limit_enforced(client: TestClient, db):
    org, user = _make_org_user(db, plan="free")  # free allows 5 sources
    headers = _auth_headers(client)
    bot_id = client.post(
        "/api/v1/chatbots", headers=headers, json={"name": "Bot"}
    ).json()["id"]

    for i in range(5):
        resp = client.post(
            f"/api/v1/chatbots/{bot_id}/knowledge-sources",
            headers=headers,
            json={"source_type": "website", "uri": f"https://example.com/{i}"},
        )
        assert resp.status_code == 201, resp.text

    resp = client.post(
        f"/api/v1/chatbots/{bot_id}/knowledge-sources",
        headers=headers,
        json={"source_type": "website", "uri": "https://example.com/overflow"},
    )
    assert resp.status_code == 402


def test_message_quota_enforced(client: TestClient, db):
    from datetime import datetime, timezone

    from app.core.billing.limits import assert_message_quota
    from fastapi import HTTPException

    org, user = _make_org_user(db, plan="free")  # 1000 msgs/month
    headers = _auth_headers(client)
    bot_id = client.post(
        "/api/v1/chatbots", headers=headers, json={"name": "Bot"}
    ).json()["id"]

    session_row = ChatSession(
        id=uuid.uuid4(),
        organization_id=org.id,
        chatbot_id=uuid.UUID(bot_id),
        customer_id="cust-1",
    )
    db.add(session_row)
    db.commit()

    # Insert messages past the limit in the current month
    for i in range(1000):
        db.add(
            Message(
                id=uuid.uuid4(),
                session_id=session_row.id,
                role="user",
                content=f"seed {i}",
            )
        )
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        assert_message_quota(db, org)
    assert exc_info.value.status_code == 402
    assert "limit" in exc_info.value.detail.lower()


def test_billing_usage_summary(client: TestClient, db):
    org, user = _make_org_user(db, plan="starter", plan_status="active")
    headers = _auth_headers(client)

    resp = client.get("/api/v1/organizations/me/billing", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["billing_enabled"] is True
    assert data["plan"] == "starter"
    assert data["limits"]["chatbots"] == 3
    assert data["usage"]["chatbots"] == 0
    assert any(p["key"] == "scale" for p in data["available_plans"])


# --- Billing feature flag (disabled = testing/dev) -----------------------


def _disable_billing(monkeypatch):
    monkeypatch.setattr(
        "app.core.billing.limits.billing_enabled", lambda: False
    )
    monkeypatch.setattr(
        "app.api.endpoints.billing.billing_enabled", lambda: False
    )


def test_checkout_returns_503_when_billing_disabled(client: TestClient, db, monkeypatch):
    _make_org_user(db)
    headers = _auth_headers(client)
    _disable_billing(monkeypatch)

    resp = client.post(
        "/api/v1/organizations/me/billing/checkout-session",
        headers=headers,
        json={"plan": "growth"},
    )
    assert resp.status_code == 503


def test_webhook_returns_503_when_billing_disabled(client: TestClient, db, monkeypatch):
    org, user = _make_org_user(db)
    payload = json.dumps(
        _sub_event("subscription.activated", "sub_1", org.id, plan="growth")
    ).encode()
    _disable_billing(monkeypatch)

    resp = client.post(
        "/api/v1/webhooks/razorpay",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": _razorpay_sign(payload),
        },
    )
    assert resp.status_code == 503


def test_chatbot_limit_not_enforced_when_billing_disabled(
    client: TestClient, db, monkeypatch
):
    org, user = _make_org_user(db, plan="free")  # free allows 1 chatbot
    headers = _auth_headers(client)
    monkeypatch.setattr(
        "app.core.billing.limits.billing_enabled", lambda: False
    )

    for i in range(3):
        resp = client.post("/api/v1/chatbots", headers=headers, json={"name": f"Bot {i}"})
        assert resp.status_code == 201


def test_cancelled_plan_downgrades_to_free(client: TestClient, db):
    org, user = _make_org_user(db, plan="growth", plan_status="cancelled")
    headers = _auth_headers(client)

    # growth allows 10 chatbots but cancelled status downgrades to free (1 chatbot)
    first = client.post("/api/v1/chatbots", headers=headers, json={"name": "Bot 1"})
    assert first.status_code == 201
    second = client.post("/api/v1/chatbots", headers=headers, json={"name": "Bot 2"})
    assert second.status_code == 402


# --- Subscription management (no self-serve portal; in-house flows) -------


def _make_subscribed_org(db, plan="growth", plan_status="active"):
    org, user = _make_org_user(db, plan=plan, plan_status=plan_status)
    org.razorpay_customer_id = "cust_sub_1"
    org.razorpay_subscription_id = "sub_mgmt_1"
    db.commit()
    return org, user


def test_subscription_detail_no_subscription(client: TestClient, db):
    _make_org_user(db)
    headers = _auth_headers(client)

    resp = client.get("/api/v1/organizations/me/billing/subscription", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_subscription"] is False
    assert data["subscription_id"] is None


def test_subscription_detail_returns_subscription_and_invoices(
    client: TestClient, db, monkeypatch
):
    _make_subscribed_org(db)
    headers = _auth_headers(client)

    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.fetch_subscription",
        lambda sid: {
            "id": sid,
            "plan_id": "plan_growth",
            "status": "active",
            "current_start": 1700000000,
            "current_end": 1702592000,
            "charge_at": 1702592000,
            "payment_method": "card",
            "cancel_at_cycle_end": False,
        },
    )
    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.list_subscription_invoices",
        lambda sid: [
            {"id": "inv_2", "status": "paid", "amount": 999900, "currency": "INR",
             "issued_at": 1702592000, "paid_at": 1702592000},
            {"id": "inv_1", "status": "issued", "amount": 999900, "currency": "INR",
             "issued_at": 1699913600, "paid_at": None},
        ],
    )

    resp = client.get("/api/v1/organizations/me/billing/subscription", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_subscription"] is True
    assert data["subscription_id"] == "sub_mgmt_1"
    assert data["plan_key"] == "growth"
    assert data["status"] == "active"
    assert data["payment_method"] == "card"
    assert len(data["invoices"]) == 2
    assert data["invoices"][0]["id"] == "inv_2"
    assert data["invoices"][0]["amount_paise"] == 999900


def test_subscription_detail_invoice_failure_is_best_effort(
    client: TestClient, db, monkeypatch
):
    from app.core.billing.razorpay_client import RazorpayError

    _make_subscribed_org(db)
    headers = _auth_headers(client)

    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.fetch_subscription",
        lambda sid: {"id": sid, "plan_id": "plan_growth", "status": "active"},
    )
    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.list_subscription_invoices",
        lambda sid: (_ for _ in ()).throw(RazorpayError("boom")),
    )

    resp = client.get("/api/v1/organizations/me/billing/subscription", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["invoices"] == []


def test_change_plan_updates_razorpay_and_org(client: TestClient, db, monkeypatch):
    org, user = _make_subscribed_org(db)
    headers = _auth_headers(client)

    captured = {}

    def fake_update_subscription(subscription_id, plan_id, schedule_change_at="now"):
        captured.update(subscription_id=subscription_id, plan_id=plan_id,
                        schedule_change_at=schedule_change_at)
        return {"id": subscription_id, "status": "active", "charge_at": 1702592000}

    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.update_subscription",
        fake_update_subscription,
    )

    resp = client.post(
        "/api/v1/organizations/me/billing/subscription/change-plan",
        headers=headers,
        json={"plan": "scale", "schedule_change_at": "now"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "scale"
    assert captured["subscription_id"] == "sub_mgmt_1"
    assert captured["plan_id"] == "plan_scale"

    db.refresh(org)
    assert org.plan == "scale"


def test_change_plan_rejects_unknown_or_free_plan(client: TestClient, db):
    _make_subscribed_org(db)
    headers = _auth_headers(client)

    for bad in ("nonexistent", "free"):
        resp = client.post(
            "/api/v1/organizations/me/billing/subscription/change-plan",
            headers=headers,
            json={"plan": bad},
        )
        assert resp.status_code == 400


def test_change_plan_requires_subscription(client: TestClient, db):
    _make_org_user(db)  # no subscription
    headers = _auth_headers(client)

    resp = client.post(
        "/api/v1/organizations/me/billing/subscription/change-plan",
        headers=headers,
        json={"plan": "growth"},
    )
    assert resp.status_code == 400


def test_cancel_subscription_calls_razorpay_and_flags_org(
    client: TestClient, db, monkeypatch
):
    org, user = _make_subscribed_org(db)
    headers = _auth_headers(client)

    captured = {}

    def fake_cancel(subscription_id, cancel_at_cycle_end=False):
        captured.update(subscription_id=subscription_id,
                        cancel_at_cycle_end=cancel_at_cycle_end)
        return {"id": subscription_id, "status": "cancelled", "current_end": 1702592000}

    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.cancel_subscription",
        fake_cancel,
    )

    resp = client.post(
        "/api/v1/organizations/me/billing/subscription/cancel",
        headers=headers,
        json={"cancel_at_cycle_end": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cancel_at_cycle_end"] is True
    assert captured["cancel_at_cycle_end"] is True

    # Cycle-end cancel keeps access until the paid period ends — enforcement
    # stays active until Razorpay fires subscription.cancelled at cycle end.
    db.refresh(org)
    assert org.plan_status == "active"


def test_cancel_subscription_immediate_flags_org_cancelled(
    client: TestClient, db, monkeypatch
):
    org, user = _make_subscribed_org(db)
    headers = _auth_headers(client)

    monkeypatch.setattr(
        "app.api.endpoints.billing.razorpay_client.cancel_subscription",
        lambda subscription_id, cancel_at_cycle_end=False: {
            "id": subscription_id, "status": "cancelled", "current_end": 1702592000,
        },
    )

    resp = client.post(
        "/api/v1/organizations/me/billing/subscription/cancel",
        headers=headers,
        json={"cancel_at_cycle_end": False},
    )
    assert resp.status_code == 200

    db.refresh(org)
    assert org.plan_status == "cancelled"


def test_cancel_subscription_requires_subscription(client: TestClient, db):
    _make_org_user(db)
    headers = _auth_headers(client)

    resp = client.post(
        "/api/v1/organizations/me/billing/subscription/cancel",
        headers=headers,
        json={},
    )
    assert resp.status_code == 400


def test_subscription_management_503_when_billing_disabled(
    client: TestClient, db, monkeypatch
):
    _make_subscribed_org(db)
    headers = _auth_headers(client)
    _disable_billing(monkeypatch)

    resp = client.get(
        "/api/v1/organizations/me/billing/subscription", headers=headers
    )
    assert resp.status_code == 503