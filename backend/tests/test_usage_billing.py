import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.ai.router import AIRouter
from app.core.billing.pricing import (
    estimate_cost_paise,
    get_model_pricing,
    overage_amount_paise,
    trim_overage_for_addon,
)
from app.models import AnalyticsEvent, LLMUsage, Organization, UsageBillingRecord, User


def _make_org_user(db, email="usage@test.com", plan="starter", plan_status="active"):
    org = Organization(
        id=uuid.uuid4(),
        name="Usage Org",
        plan=plan,
        plan_status=plan_status,
        razorpay_subscription_id="sub_usage_test",
    )
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hashed",
        organization_id=org.id,
        role="admin",
    )
    db.add(user)
    db.commit()
    return org, user


def _add_usage(db, org, prompt=10_000, completion=5_000, model="gpt-4o-mini", ts=None):
    usage = LLMUsage(
        id=uuid.uuid4(),
        organization_id=org.id,
        model=model,
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        cost=estimate_cost_paise(model, prompt, completion),
        timestamp=ts or datetime.now(timezone.utc),
    )
    db.add(usage)
    db.commit()
    return usage


def _auth_headers(client, email="usage@test.com"):
    return {"X-Test-User": email}


# --- Pricing -------------------------------------------------------------


def test_get_model_pricing_matches_by_substring():
    assert get_model_pricing("openai/gpt-4o-mini") == get_model_pricing("gpt-4o-mini")
    assert get_model_pricing("unknown-model") == (15, 60)


def test_estimate_cost_paise_math():
    # gpt-4o-mini: input 5 paise/1k, output 20 paise/1k
    cost = estimate_cost_paise("gpt-4o-mini", 10_000, 5_000)
    assert cost == round(10_000 * 5 / 1000 + 5_000 * 20 / 1000)
    assert estimate_cost_paise("gpt-4o-mini", 0, 0) == 0


def test_overage_amount_paise_math():
    assert overage_amount_paise(100_000, 40) == round(100_000 * 40 / 1000)


def test_trim_overage_for_addon_caps_batch():
    billable, deferred = trim_overage_for_addon(6_000_000)
    assert billable == 5_000_000
    assert deferred == 1_000_000


# --- Billing beat task ---------------------------------------------------


def test_aggregate_usage_billing_creates_record(db):
    from app.tasks.billing_tasks import aggregate_usage_billing

    org, _ = _make_org_user(db)
    _add_usage(db, org, prompt=50_000, completion=25_000)

    result = aggregate_usage_billing()

    assert result["status"] == "completed"
    record = (
        db.query(UsageBillingRecord)
        .filter(UsageBillingRecord.organization_id == org.id)
        .first()
    )
    assert record is not None
    assert record.total_tokens == 75_000
    assert record.prompt_tokens == 50_000
    assert record.completion_tokens == 25_000
    assert record.estimated_cost == estimate_cost_paise("gpt-4o-mini", 50_000, 25_000)
    assert record.overage_tokens == 0


def test_aggregate_usage_billing_upserts_single_record(db):
    from app.tasks.billing_tasks import aggregate_usage_billing

    org, _ = _make_org_user(db)
    _add_usage(db, org, prompt=10_000, completion=5_000)
    _add_usage(db, org, prompt=20_000, completion=10_000)

    aggregate_usage_billing()
    aggregate_usage_billing()

    records = (
        db.query(UsageBillingRecord)
        .filter(UsageBillingRecord.organization_id == org.id)
        .all()
    )
    assert len(records) == 1
    assert records[0].total_tokens == 45_000


def test_aggregate_reports_overage_to_razorpay(db, monkeypatch):
    from app.tasks import billing_tasks

    org, _ = _make_org_user(db)
    # starter includes 1,000,000 tokens; go over by 100k
    _add_usage(db, org, prompt=1_050_000, completion=50_000)

    captured = {}

    def fake_create_addon(subscription_id, name, amount_paise, description=None, notes=None):
        captured.update(
            subscription_id=subscription_id,
            name=name,
            amount_paise=amount_paise,
            notes=notes,
        )
        return {"id": "addon_test_1"}

    monkeypatch.setattr(
        "app.core.billing.razorpay_client.create_addon", fake_create_addon
    )
    monkeypatch.setattr("app.core.billing.limits.billing_enabled", lambda: True)

    result = billing_tasks.aggregate_usage_billing()

    record = (
        db.query(UsageBillingRecord)
        .filter(UsageBillingRecord.organization_id == org.id)
        .first()
    )
    assert result["status"] == "completed"
    assert record.reported_to_razorpay is True
    assert record.razorpay_addon_id == "addon_test_1"
    assert record.overage_tokens == 100_000
    assert captured["subscription_id"] == "sub_usage_test"
    assert captured["amount_paise"] == overage_amount_paise(100_000, 40)


def test_aggregate_falls_back_when_addon_fails(db, monkeypatch):
    from app.tasks import billing_tasks
    from app.core.billing.razorpay_client import RazorpayError

    org, _ = _make_org_user(db)
    _add_usage(db, org, prompt=1_050_000, completion=50_000)

    def fake_create_addon(*args, **kwargs):
        raise RazorpayError("boom")

    monkeypatch.setattr(
        "app.core.billing.razorpay_client.create_addon", fake_create_addon
    )
    monkeypatch.setattr("app.core.billing.limits.billing_enabled", lambda: True)

    result = billing_tasks.aggregate_usage_billing()

    record = (
        db.query(UsageBillingRecord)
        .filter(UsageBillingRecord.organization_id == org.id)
        .first()
    )
    assert result["status"] == "completed"
    assert record.reported_to_razorpay is False
    assert record.razorpay_addon_id is None
    assert record.overage_tokens == 100_000


def test_aggregate_does_not_report_without_subscription(db, monkeypatch):
    from app.tasks import billing_tasks

    org, _ = _make_org_user(db)
    org.razorpay_subscription_id = None
    db.commit()
    _add_usage(db, org, prompt=1_050_000, completion=50_000)

    monkeypatch.setattr("app.core.billing.limits.billing_enabled", lambda: True)

    result = billing_tasks.aggregate_usage_billing()
    record = (
        db.query(UsageBillingRecord)
        .filter(UsageBillingRecord.organization_id == org.id)
        .first()
    )
    assert result["status"] == "completed"
    assert record.reported_to_razorpay is False


def test_aggregate_fires_soft_limit_event_once(db, monkeypatch):
    from app.tasks import billing_tasks

    org, _ = _make_org_user(db)
    # starter includes 1,000,000; 90% triggers the soft limit
    _add_usage(db, org, prompt=900_000, completion=0)

    monkeypatch.setattr("app.core.billing.limits.billing_enabled", lambda: True)

    billing_tasks.aggregate_usage_billing()
    billing_tasks.aggregate_usage_billing()

    events = (
        db.query(AnalyticsEvent)
        .filter(
            AnalyticsEvent.organization_id == org.id,
            AnalyticsEvent.event_type == "billing.usage_soft_limit",
        )
        .all()
    )
    assert len(events) == 1
    assert events[0].payload["ratio"] == pytest.approx(0.9)
    assert events[0].payload["plan"] == "starter"


def test_aggregate_no_soft_limit_below_threshold(db, monkeypatch):
    from app.tasks import billing_tasks

    org, _ = _make_org_user(db)
    _add_usage(db, org, prompt=100_000, completion=0)

    monkeypatch.setattr("app.core.billing.limits.billing_enabled", lambda: True)

    billing_tasks.aggregate_usage_billing()
    events = (
        db.query(AnalyticsEvent)
        .filter(
            AnalyticsEvent.organization_id == org.id,
            AnalyticsEvent.event_type == "billing.usage_soft_limit",
        )
        .all()
    )
    assert len(events) == 0


# --- Billing endpoint surfaces warning + usage billing -------------------


def test_usage_summary_includes_warning_and_usage_billing(client: TestClient, db, monkeypatch):
    from app.core.security import hash_password
    from app.tasks import billing_tasks

    org = Organization(
        id=uuid.uuid4(),
        name="Usage Org",
        plan="starter",
        plan_status="active",
        razorpay_subscription_id="sub_usage_test",
    )
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email="usage@test.com",
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role="admin",
    )
    db.add(user)
    db.commit()

    _add_usage(db, org, prompt=900_000, completion=0)
    monkeypatch.setattr("app.core.billing.limits.billing_enabled", lambda: True)
    billing_tasks.aggregate_usage_billing()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "usage@test.com", "password": "testpass123"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = client.get("/api/v1/organizations/me/billing", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["warning"] is not None
    assert data["warning"]["type"] == "usage_soft_limit"
    assert data["usage_billing"] is not None
    assert data["usage_billing"]["total_tokens"] == 900_000
    assert data["limits"]["included_monthly_tokens"] == 1_000_000


# --- LLMUsage recording in pipeline -------------------------------------


def test_pipeline_records_llm_usage(db):
    from app.core.pipeline.response_pipeline import ResponsePipeline

    org, _ = _make_org_user(db)

    pipeline = ResponsePipeline()
    pipeline.ai = AIRouter(behaviour="balanced")
    pipeline.ai.last_usage = {
        "model": "gpt-4o-mini",
        "prompt_tokens": 123,
        "completion_tokens": 45,
        "total_tokens": 168,
    }

    pipeline._record_usage(db, str(org.id), None)
    db.commit()

    rows = db.query(LLMUsage).filter(LLMUsage.organization_id == org.id).all()
    assert len(rows) == 1
    assert rows[0].total_tokens == 168
    assert rows[0].model == "gpt-4o-mini"
    assert rows[0].cost == estimate_cost_paise("gpt-4o-mini", 123, 45)


def test_pipeline_skips_recording_without_db():
    from app.core.pipeline.response_pipeline import ResponsePipeline

    pipeline = ResponsePipeline()
    pipeline.ai = AIRouter(behaviour="balanced")
    pipeline.ai.last_usage = {"model": "gpt-4o-mini", "prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}

    # Should not raise with db=None
    pipeline._record_usage(None, "org", None)


def test_ai_router_captures_usage():
    router = AIRouter(behaviour="balanced")
    assert router.last_usage is None


def test_ai_router_capture_usage_with_provider_response():
    from app.core.ai.router import AIRouter

    router = AIRouter(behaviour="balanced")

    class FakeUsage:
        prompt_tokens = 100
        completion_tokens = 50
        total_tokens = 150

    class FakeResponse:
        usage = FakeUsage()

    usage = router._capture_usage("gpt-4o-mini", [{"content": "hi"}], "hello", FakeResponse())
    assert usage["prompt_tokens"] == 100
    assert usage["completion_tokens"] == 50
    assert usage["total_tokens"] == 150
    assert usage["model"] == "gpt-4o-mini"
