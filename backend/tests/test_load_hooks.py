"""Verifies load-test hooks: mock LLM mode, per-stage timings header, per-org rate limit."""
import json
from uuid import UUID

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import create_access_token


@pytest.fixture
def widget_override(client, db):
    """Override the widget-session dependency so SQLite tests skip SET LOCAL (Postgres RLS)."""
    from app.api.endpoints import widget_api
    from app.models import ChatSession
    from app.core.security import decode_token

    def _fake_get_widget_session(request: Request, db: Session = Depends(get_db)):
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "")
        payload = decode_token(token)
        sess = db.query(ChatSession).filter(ChatSession.id == UUID(payload["sub"])).first()
        return sess

    app = client.app
    app.dependency_overrides[widget_api.get_widget_session] = _fake_get_widget_session
    yield
    app.dependency_overrides.pop(widget_api.get_widget_session, None)


def _seed_widget(client: TestClient, db):
    from app.models import ChatSession, Chatbot, Organization

    org = Organization(name="LT Org", plan="free", plan_status="active")
    db.add(org)
    db.commit()
    db.refresh(org)
    bot = Chatbot(organization_id=org.id, name="Bot", behaviour="balanced")
    db.add(bot)
    db.commit()
    db.refresh(bot)
    sess = ChatSession(organization_id=org.id, chatbot_id=bot.id, customer_id="c")
    db.add(sess)
    db.commit()
    db.refresh(sess)
    org_id, bot_id, sess_id = str(org.id), str(bot.id), str(sess.id)
    token = create_access_token(
        subject=sess_id,
        organization_id=org_id,
        extra_claims={"type": "widget", "chatbot_id": bot_id},
    )
    return {"org_id": org_id, "session_id": sess_id, "token": token}


@pytest.fixture
def mock_llm_enabled():
    s = get_settings()
    orig = (s.mock_llm, s.celery_enabled, s.redis_url)
    s.mock_llm = True
    s.celery_enabled = False
    s.redis_url = ""
    yield
    s.mock_llm, s.celery_enabled, s.redis_url = orig


def test_widget_message_returns_timings_header(client, db, mock_llm_enabled, widget_override):
    ctx = _seed_widget(client, db)
    r = client.post(
        "/api/v1/widget/messages",
        headers={"Authorization": f"Bearer {ctx['token']}"},
        json={"session_id": ctx["session_id"], "content": "hello"},
    )
    assert r.status_code == 200, r.text[:800]
    timings = json.loads(r.headers["X-Pipeline-Timings"])
    assert "cache_lookup" in timings
    assert "retrieval" in timings
    assert "llm_generate" in timings
    assert timings["total"] > 0
    assert "[mock]" in r.json()["reply"]


def test_mock_llm_never_calls_provider(mock_llm_enabled):
    from app.core.ai.router import AIRouter

    with patch("app.core.ai.router.litellm_completion") as mock:
        router = AIRouter()
        reply = router.generate([{"role": "user", "content": "hi"}])
        assert "[mock]" in reply
        mock.assert_not_called()
        assert router.last_usage and router.last_usage["model"]


def test_per_org_rate_limit_429(client, db, monkeypatch, widget_override, mock_llm_enabled):
    ctx = _seed_widget(client, db)
    # Force a tiny per-org limit to observe the 429 path.
    monkeypatch.setattr(get_settings(), "rate_limit_per_org", "3/minute")
    for _ in range(3):
        r = client.post(
            "/api/v1/widget/messages",
            headers={"Authorization": f"Bearer {ctx['token']}"},
            json={"session_id": ctx["session_id"], "content": "x"},
        )
        assert r.status_code == 200
    r4 = client.post(
        "/api/v1/widget/messages",
        headers={"Authorization": f"Bearer {ctx['token']}"},
        json={"session_id": ctx["session_id"], "content": "x"},
    )
    assert r4.status_code == 429


def test_per_org_rate_limit_keyed_per_org(client, db, monkeypatch, widget_override, mock_llm_enabled):
    """Two different orgs are limited independently (no cross-org starvation)."""
    monkeypatch.setattr(get_settings(), "rate_limit_per_org", "2/minute")
    a = _seed_widget(client, db)
    b = _seed_widget(client, db)
    for _ in range(2):
        assert (
            client.post(
                "/api/v1/widget/messages",
                headers={"Authorization": f"Bearer {a['token']}"},
                json={"session_id": a["session_id"], "content": "x"},
            ).status_code
            == 200
        )
    # Org A now over its 2/min limit; Org B is untouched and still succeeds.
    assert (
        client.post(
            "/api/v1/widget/messages",
            headers={"Authorization": f"Bearer {a['token']}"},
            json={"session_id": a["session_id"], "content": "x"},
        ).status_code
        == 429
    )
    assert (
        client.post(
            "/api/v1/widget/messages",
            headers={"Authorization": f"Bearer {b['token']}"},
            json={"session_id": b["session_id"], "content": "x"},
        ).status_code
        == 200
    )