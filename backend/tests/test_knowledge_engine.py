from unittest.mock import MagicMock, patch

import pytest

from app.core.knowledge.embeddings import EmbeddingService
from app.core.knowledge.engine import KnowledgeEngine
from app.core.knowledge.qdrant_store import QdrantStore


@pytest.fixture
def mock_qdrant():
    with patch("app.core.knowledge.qdrant_store.QdrantClient") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_embeddings():
    with patch("app.core.knowledge.embeddings.litellm_embedding") as mock:
        mock.return_value = MagicMock(
            data=[{"embedding": [0.1] * 384} for _ in range(3)]
        )
        yield mock


@pytest.fixture
def engine(mock_qdrant, mock_embeddings):
    return KnowledgeEngine()


def test_index_chunks(engine, mock_qdrant):
    chunks = [
        ("chunk1 text", {"source_id": "src1", "organization_id": "org1", "chatbot_id": "bot1", "chunk_index": 0}),
        ("chunk2 text", {"source_id": "src1", "organization_id": "org1", "chatbot_id": "bot1", "chunk_index": 1}),
    ]
    engine.index_chunks(chunks)
    assert mock_qdrant.upsert.called


def test_retrieve_with_filters(engine, mock_qdrant):
    mock_qdrant.search.return_value = [
        MagicMock(
            id=1,
            score=0.95,
            payload={"text": "result text", "source_id": "src1", "chunk_index": 0},
        )
    ]
    results = engine.retrieve(
        query="test query",
        organization_id="org1",
        chatbot_id="bot1",
    )
    assert len(results) == 1
    assert results[0]["score"] == 0.95
    assert results[0]["text"] == "result text"


def test_retrieve_empty_results(engine, mock_qdrant):
    mock_qdrant.search.return_value = []
    results = engine.retrieve(
        query="no match",
        organization_id="org1",
    )
    assert results == []


def test_filter_by_policy_source_filter(engine):
    results = [
        {"source_id": "src1", "text": "content 1", "score": 0.9},
        {"source_id": "src2", "text": "content 2", "score": 0.8},
    ]
    policy = MagicMock()
    policy.policy_type = "source_filter"
    policy.rules = {"allowed_source_ids": ["src1"]}

    filtered = engine._filter_by_policies(results, [policy])
    assert len(filtered) == 1
    assert filtered[0]["source_id"] == "src1"


def test_filter_by_policy_content_filter(engine):
    results = [
        {"source_id": "src1", "text": "this is safe content", "score": 0.9},
        {"source_id": "src2", "text": "this has blocked term", "score": 0.8},
    ]
    policy = MagicMock()
    policy.policy_type = "content_filter"
    policy.rules = {"blocked_terms": ["blocked"]}

    filtered = engine._filter_by_policies(results, [policy])
    assert len(filtered) == 1
    assert "blocked" not in filtered[0]["text"]


def test_retrieve_formatted_context(engine, mock_qdrant):
    mock_qdrant.search.return_value = [
        MagicMock(
            id=1,
            score=0.95,
            payload={"text": "first chunk", "source_id": "src1", "chunk_index": 0},
        ),
        MagicMock(
            id=2,
            score=0.85,
            payload={"text": "second chunk", "source_id": "src1", "chunk_index": 1},
        ),
    ]
    context = engine.retrieve_formatted_context(
        query="test",
        organization_id="org1",
    )
    assert "[Source 1]" in context
    assert "[Source 2]" in context
    assert "first chunk" in context
    assert "second chunk" in context
