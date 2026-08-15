import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models import Chatbot, DailyAnalytics, Organization, User


def _make_org_user(db, email, role="admin"):
    org = Organization(id=uuid.uuid4(), name=f"Org {email}")
    db.add(org)
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role=role,
    )
    db.add(user)
    db.commit()
    return org, user


def _auth_headers(client, email):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_bot(client, headers):
    resp = client.post("/api/v1/chatbots", headers=headers, json={"name": "Bot"})
    return resp.json()["id"]


def _seed_daily(db, org_id, chatbot_id, day, messages=5, sessions=2, tokens=100):
    da = DailyAnalytics(
        id=uuid.uuid4(),
        date=day,
        organization_id=uuid.UUID(str(org_id)),
        chatbot_id=uuid.UUID(str(chatbot_id)),
        entity_type="chatbot",
        sessions_count=sessions,
        messages_count=messages,
        prompt_tokens=tokens,
        completion_tokens=tokens,
        total_tokens=tokens * 2,
        avg_latency_ms=42.0,
        feedback_positive=3,
        feedback_negative=1,
    )
    db.add(da)
    db.commit()


def test_org_daily_analytics_time_series(client: TestClient, db):
    org, user = _make_org_user(db, "series@test.com")
    headers = _auth_headers(client, "series@test.com")
    bot_id = _create_bot(client, headers)

    today = date.today()
    _seed_daily(db, org.id, bot_id, today - timedelta(days=2), messages=10, tokens=200)
    _seed_daily(db, org.id, bot_id, today - timedelta(days=1), messages=20, tokens=400)

    response = client.get(
        f"/api/v1/analytics/organization/daily?start_date={(today - timedelta(days=3)).isoformat()}&end_date={today.isoformat()}",
        headers=headers,
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    assert {r["messages_count"] for r in rows} == {10, 20}
    assert {r["total_tokens"] for r in rows} == {400, 800}
    assert all(r["avg_latency_ms"] == 42.0 for r in rows)
    assert all(r["organization_id"] == str(org.id) for r in rows)


def test_org_daily_analytics_respects_date_range(client: TestClient, db):
    org, user = _make_org_user(db, "range@test.com")
    headers = _auth_headers(client, "range@test.com")
    bot_id = _create_bot(client, headers)

    today = date.today()
    _seed_daily(db, org.id, bot_id, today - timedelta(days=10))
    _seed_daily(db, org.id, bot_id, today - timedelta(days=1))

    response = client.get(
        f"/api/v1/analytics/organization/daily?start_date={(today - timedelta(days=2)).isoformat()}",
        headers=headers,
    )
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["date"] == (today - timedelta(days=1)).isoformat()


def test_org_daily_analytics_never_leaks_other_org(client: TestClient, db):
    org_a, user_a = _make_org_user(db, "isola@test.com")
    org_b, user_b = _make_org_user(db, "isola_b@test.com")

    headers_a = _auth_headers(client, "isola@test.com")
    headers_b = _auth_headers(client, "isola_b@test.com")

    bot_a = _create_bot(client, headers_a)
    bot_b = _create_bot(client, headers_b)

    _seed_daily(db, org_a.id, bot_a, date.today())
    _seed_daily(db, org_b.id, bot_b, date.today())

    response = client.get("/api/v1/analytics/organization/daily", headers=headers_a)
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["chatbot_id"] == bot_a
    assert all(r["organization_id"] == str(org_a.id) for r in rows)


def test_chatbot_daily_analytics_scoped(client: TestClient, db):
    org, user = _make_org_user(db, "chatseries@test.com")
    headers = _auth_headers(client, "chatseries@test.com")
    bot_id = _create_bot(client, headers)

    today = date.today()
    _seed_daily(db, org.id, bot_id, today - timedelta(days=1))

    response = client.get(
        f"/api/v1/analytics/chatbot/{bot_id}/daily",
        headers=headers,
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["chatbot_id"] == bot_id


def test_chatbot_daily_cross_org_returns_404(client: TestClient, db):
    org_a, user_a = _make_org_user(db, "xorga@test.com")
    org_b, user_b = _make_org_user(db, "xorgb@test.com")

    headers_a = _auth_headers(client, "xorga@test.com")
    headers_b = _auth_headers(client, "xorgb@test.com")

    bot_b = _create_bot(client, headers_b)

    response = client.get(
        f"/api/v1/analytics/chatbot/{bot_b}/daily",
        headers=headers_a,
    )
    assert response.status_code == 404


def test_chatbot_analytics_aggregate_cross_org_returns_404(client: TestClient, db):
    org_a, user_a = _make_org_user(db, "agg_a@test.com")
    org_b, user_b = _make_org_user(db, "agg_b@test.com")

    headers_a = _auth_headers(client, "agg_a@test.com")
    headers_b = _auth_headers(client, "agg_b@test.com")

    bot_b = _create_bot(client, headers_b)

    response = client.get(
        f"/api/v1/analytics/chatbot/{bot_b}",
        headers=headers_a,
    )
    assert response.status_code == 404


def test_org_analytics_aggregate_scoped_to_own_org(client: TestClient, db):
    org, user = _make_org_user(db, "orggag@test.com")
    headers = _auth_headers(client, "orggag@test.com")
    bot_id = _create_bot(client, headers)

    response = client.get("/api/v1/analytics/organization", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["organization_id"] == str(org.id)
    assert data["total_chatbots"] == 1


def test_analytics_requires_auth(client: TestClient, db):
    response = client.get("/api/v1/analytics/organization/daily")
    assert response.status_code == 401 or response.status_code == 403


def test_auth_me_returns_current_user(client: TestClient, db):
    org, user = _make_org_user(db, "me@test.com")
    headers = _auth_headers(client, "me@test.com")

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["organization_id"] == str(org.id)
    assert data["role"] == "admin"