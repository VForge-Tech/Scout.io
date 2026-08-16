"""Tests for the reranker FastAPI service (services/reranker/app/main.py).

These exercise the service logic with a mocked encoder so the suite doesn't
need to download the cross-encoder model.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def _client():
    return TestClient(app)


def test_health():
    with TestClient(app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_rerank_reorders_by_score():
    fake_encoder = MagicMock()
    fake_encoder.predict.return_value = [0.2, 0.9, 0.5]
    with TestClient(app) as c, patch("app.main.get_encoder", return_value=fake_encoder):
        r = c.post(
            "/rerank",
            json={
                "query": "how to reset password",
                "chunks": [
                    {"id": "a", "text": "password reset instructions", "score": 0.8},
                    {"id": "b", "text": "billing tiers and pricing", "score": 0.7},
                    {"id": "c", "text": "team invitations and roles", "score": 0.6},
                ],
            },
        )
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()["results"]]
        assert ids == ["b", "c", "a"]
        scores = [item["score"] for item in r.json()["results"]]
        assert scores == [0.9, 0.5, 0.2]


def test_rerank_top_k_limits_results():
    fake_encoder = MagicMock()
    fake_encoder.predict.return_value = [0.1, 0.8, 0.4]
    with TestClient(app) as c, patch("app.main.get_encoder", return_value=fake_encoder):
        r = c.post(
            "/rerank",
            json={
                "query": "q",
                "top_k": 2,
                "chunks": [
                    {"id": "a", "text": "x", "score": 1.0},
                    {"id": "b", "text": "y", "score": 0.9},
                    {"id": "c", "text": "z", "score": 0.8},
                ],
            },
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 2
        assert r.json()["results"][0]["id"] == "b"


def test_rerank_validates_empty_chunks():
    with TestClient(app) as c:
        r = c.post("/rerank", json={"query": "q", "chunks": []})
        assert r.status_code == 422


def test_ready_reports_model_loaded():
    fake_encoder = MagicMock()
    with TestClient(app) as c, patch("app.main.get_encoder", return_value=fake_encoder):
        r = c.get("/ready")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"