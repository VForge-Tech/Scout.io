"""Tests for the cross-encoder reranker client and KnowledgeEngine integration."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import get_settings
from app.core.knowledge.engine import KnowledgeEngine
from app.core.knowledge.reranker import RerankerClient, RerankerUnavailable


class TestRerankerClient:
    def test_rerank_returns_reordered_chunks(self):
        with patch("app.core.knowledge.reranker.httpx.post") as mock_post:
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "results": [
                    {"id": "c2", "text": "two", "score": 0.9},
                    {"id": "c1", "text": "one", "score": 0.5},
                ]
            }
            mock_post.return_value = resp

            client = RerankerClient(url="http://reranker:8082")
            out = client.rerank(
                "query",
                [{"id": "c1", "text": "one", "score": 0.8}, {"id": "c2", "text": "two", "score": 0.7}],
            )
            assert [o["id"] for o in out] == ["c2", "c1"]
            assert out[0]["rerank_score"] == 0.9
            assert out[1]["rerank_score"] == 0.5

    def test_rerank_retries_then_raises(self):
        with patch("app.core.knowledge.reranker.httpx.post") as mock_post:
            resp = MagicMock()
            resp.status_code = 500
            mock_post.return_value = resp

            client = RerankerClient(url="http://reranker:8082", retries=2)
            with pytest.raises(RerankerUnavailable):
                client.rerank("q", [{"id": "c1", "text": "t"}])
            assert mock_post.call_count == 3

    def test_rerank_transport_error_raises(self):
        with patch("app.core.knowledge.reranker.httpx.post") as mock_post:
            mock_post.side_effect = Exception("connection refused")
            client = RerankerClient(url="http://reranker:8082", retries=1)
            with pytest.raises(RerankerUnavailable):
                client.rerank("q", [{"id": "c1", "text": "t"}])


class TestKnowledgeEngineRerank:
    def _results(self):
        return [
            {"id": "c1", "text": "one", "score": 0.8, "source_id": "s1", "chunk_index": 0},
            {"id": "c2", "text": "two", "score": 0.7, "source_id": "s1", "chunk_index": 1},
            {"id": "c3", "text": "three", "score": 0.6, "source_id": "s1", "chunk_index": 2},
        ]

    def test_rerank_enabled_reranks_and_merges_metadata(self):
        engine = KnowledgeEngine()
        with patch.object(
            engine.reranker, "rerank", return_value=[
                {"id": "c3", "text": "three", "score": 0.95, "rerank_score": 0.95},
                {"id": "c1", "text": "one", "score": 0.7, "rerank_score": 0.7},
                {"id": "c2", "text": "two", "score": 0.4, "rerank_score": 0.4},
            ]
        ) as mock_rerank:
            out = engine._rerank("q", self._results(), enabled=True, top_k=3)
            assert [r["id"] for r in out] == ["c3", "c1", "c2"]
            # Original metadata preserved from Qdrant result
            assert out[0]["source_id"] == "s1"
            assert out[0]["chunk_index"] == 2
            # score replaced by reranker score
            assert out[0]["score"] == 0.95
            mock_rerank.assert_called_once()

    def test_rerank_disabled_returns_original_order(self):
        engine = KnowledgeEngine()
        with patch.object(engine.reranker, "rerank") as mock_rerank:
            out = engine._rerank("q", self._results(), enabled=False, top_k=3)
            assert [r["id"] for r in out] == ["c1", "c2", "c3"]
            mock_rerank.assert_not_called()

    def test_rerank_global_flag_controls_default(self, monkeypatch):
        engine = KnowledgeEngine()
        monkeypatch.setattr(get_settings(), "reranker_enabled", True)
        with patch.object(
            engine.reranker, "rerank", return_value=[]
        ) as mock_rerank:
            out = engine._rerank("q", self._results(), enabled=None, top_k=3)
            assert [r["id"] for r in out] == ["c1", "c2", "c3"]  # empty rerank -> original
            mock_rerank.assert_called_once()

    def test_rerank_fallback_on_unavailable(self):
        """Reranker failure must NOT propagate; falls back to Qdrant order."""
        engine = KnowledgeEngine()
        with patch.object(
            engine.reranker,
            "rerank",
            side_effect=RerankerUnavailable("down"),
        ) as mock_rerank:
            out = engine._rerank("q", self._results(), enabled=True, top_k=3)
            assert [r["id"] for r in out] == ["c1", "c2", "c3"]
            mock_rerank.assert_called_once()

    def test_rerank_fallback_any_exception(self):
        engine = KnowledgeEngine()
        with patch.object(engine.reranker, "rerank", side_effect=RuntimeError("boom")):
            out = engine._rerank("q", self._results(), enabled=True, top_k=3)
            assert [r["id"] for r in out] == ["c1", "c2", "c3"]

    def test_retrieve_reranks_after_search(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "reranker_enabled", True)
        engine = KnowledgeEngine()
        engine.store = MagicMock()
        engine.store.search.return_value = self._results()
        with patch.object(
            engine.reranker,
            "rerank",
            return_value=[
                {"id": "c3", "text": "three", "score": 0.99, "rerank_score": 0.99},
                {"id": "c1", "text": "one", "score": 0.6, "rerank_score": 0.6},
                {"id": "c2", "text": "two", "score": 0.3, "rerank_score": 0.3},
            ],
        ) as mock_rerank:
            out = engine.retrieve(
                query="q", organization_id="org1", chatbot_id="bot1"
            )
            assert [r["id"] for r in out] == ["c3", "c1", "c2"]
            mock_rerank.assert_called_once()

    def test_retrieve_fallback_keeps_qdrant_order(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "reranker_enabled", True)
        engine = KnowledgeEngine()
        engine.store = MagicMock()
        engine.store.search.return_value = self._results()
        with patch.object(engine.reranker, "rerank", side_effect=RerankerUnavailable("down")):
            out = engine.retrieve(query="q", organization_id="org1")
            assert [r["id"] for r in out] == ["c1", "c2", "c3"]