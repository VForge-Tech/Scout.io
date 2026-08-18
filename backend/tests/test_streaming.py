"""SSE streaming endpoint tests for the public widget and the dashboard playground."""
import json
from uuid import UUID

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import create_access_token, decode_token


@pytest.fixture
def mock_llm_enabled():
    s = get_settings()
    orig = (s.mock_llm, s.celery_enabled, s.redis_url)
    s.mock_llm = True
    s.celery_enabled = False
    s.redis_url = ""
    yield
    s.mock_llm, s.celery_enabled, s.redis_url = orig


@pytest.fixture
def widget_override(client, db):
    """Override the widget-session dependency so SQLite tests skip SET LOCAL (Postgres RLS)."""
    from app.api.endpoints import widget_api
    from app.models import ChatSession

    def _fake_get_widget_session(request: Request, db: Session = Depends(get_db)):
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "")
        payload = decode_token(token)
        return db.query(ChatSession).filter(ChatSession.id == UUID(payload["sub"])).first()

    app = client.app
    app.dependency_overrides[widget_api.get_widget_session] = _fake_get_widget_session
    yield
    app.dependency_overrides.pop(widget_api.get_widget_session, None)


def _seed_widget(client: TestClient, db):
    from app.models import ChatSession, Chatbot, Organization

    org = Organization(name="Stream Org", plan="free", plan_status="active")
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


def _seed_org_user(db):
    from app.core.security import hash_password
    from app.models import Chatbot, Organization, User

    org = Organization(name="Stream Org", plan="free", plan_status="active")
    db.add(org)
    db.commit()
    db.refresh(org)
    bot = Chatbot(organization_id=org.id, name="Bot", behaviour="balanced")
    db.add(bot)
    db.commit()
    db.refresh(bot)
    user = User(
        email="stream@test.com",
        hashed_password=hash_password("testpass123"),
        organization_id=org.id,
        role="admin",
        full_name="Admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return org, bot, user


def _parse_sse(text: str):
    events = []
    for frame in text.split("\n\n"):
        for line in frame.split("\n"):
            if line.startswith("data:"):
                events.append(json.loads(line[5:].strip()))
    return events


def test_widget_message_stream(client, db, mock_llm_enabled, widget_override):
    ctx = _seed_widget(client, db)
    r = client.post(
        "/api/v1/widget/messages/stream",
        headers={"Authorization": f"Bearer {ctx['token']}"},
        json={"session_id": ctx["session_id"], "content": "hello"},
    )
    assert r.status_code == 200, r.text[:800]
    assert "text/event-stream" in r.headers["content-type"]
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert types[0] == "meta"
    assert "done" in types
    done = next(e for e in events if e["type"] == "done")
    assert "[mock]" in done["reply"]
    assert "time_to_first_token_ms" in done
    assert "total_latency_ms" in done


def test_playground_stream_endpoint(client, db, mock_llm_enabled):
    _org, bot, _user = _seed_org_user(db)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "stream@test.com", "password": "testpass123"},
    )
    token = resp.json()["access_token"]
    r = client.post(
        f"/api/v1/chatbots/{bot.id}/messages/stream",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "hello"},
    )
    assert r.status_code == 200, r.text[:800]
    assert "text/event-stream" in r.headers["content-type"]
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert types[0] == "meta"
    assert "done" in types
    done = next(e for e in events if e["type"] == "done")
    assert "[mock]" in done["reply"]
    assert done["time_to_first_token_ms"] is not None
    assert done["total_latency_ms"] is not None