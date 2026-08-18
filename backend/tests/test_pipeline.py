from unittest.mock import MagicMock, patch

import pytest

from app.core.memory.knowledge_memory import KnowledgeMemory
from app.core.memory.optimization_memory import OptimizationMemory
from app.core.memory.session_memory import SessionMemory
from app.core.pipeline.response_pipeline import ResponsePipeline


@pytest.fixture
def mock_redis_client():
    return MagicMock()


@pytest.fixture
def pipeline(mock_redis_client):
    with (
        patch("app.core.knowledge.qdrant_store.QdrantClient") as mock_qdrant,
        patch("app.core.ai.router.litellm_completion") as mock_llm,
        patch("app.core.knowledge.embeddings.litellm_embedding") as mock_emb,
    ):
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Test reply"))]
        )
        mock_emb.return_value = MagicMock(
            data=[{"embedding": [0.1] * 384} for _ in range(3)]
        )
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.search.return_value = [
            MagicMock(
                id=1,
                score=0.95,
                payload={"text": "Retrieved context", "source_id": "src1", "chunk_index": 0},
            )
        ]
        mock_qdrant.return_value = mock_qdrant_client

        yield ResponsePipeline(
            session_memory=SessionMemory(redis_client=mock_redis_client),
            knowledge_memory=KnowledgeMemory(redis_client=mock_redis_client),
            opt_memory=OptimizationMemory(redis_client=mock_redis_client),
        )


def test_pipeline_full_flow(pipeline, mock_redis_client):
    mock_redis_client.get.return_value = None
    mock_redis_client.lrange.return_value = []
    result = pipeline.run(
        query="What is Scout?",
        session_id="test-session-1",
        organization_id="org-1",
        chatbot_id="bot-1",
    )
    assert "reply" in result
    assert result["reply"] == "Test reply"
    assert not result.get("cached", False)
    assert result["session_id"] == "test-session-1"


def test_pipeline_cached_response(pipeline, mock_redis_client):
    mock_redis_client.get.return_value = b"Cached reply"
    result = pipeline.run(
        query="test query",
        session_id="test-session-2",
        organization_id="org-1",
    )
    assert result["reply"] == "Cached reply"
    assert result["cached"]


def test_pipeline_with_policies(pipeline, mock_redis_client):
    mock_redis_client.get.return_value = None
    mock_redis_client.lrange.return_value = []
    policy = MagicMock()
    policy.policy_type = "source_filter"
    policy.rules = {"allowed_source_ids": ["src1"]}

    result = pipeline.run(
        query="test",
        session_id="test-session-3",
        organization_id="org-1",
        policies=[policy],
    )
    assert result["reply"] is not None


def test_pipeline_run_stream_yields_tokens_and_done(pipeline, mock_redis_client):
    mock_redis_client.get.return_value = None
    mock_redis_client.lrange.return_value = []
    with patch.object(pipeline.ai, "generate_stream", return_value=iter(["Hel", "lo"])):
        events = list(
            pipeline.run_stream(
                query="What is Scout?",
                session_id="test-session-stream-1",
                organization_id="org-1",
                chatbot_id="bot-1",
            )
        )
    types = [e["type"] for e in events]
    assert types[0] == "meta"
    assert "token" in types
    assert types[-1] == "done"
    done = events[-1]
    assert done["reply"] == "Hello"
    assert "time_to_first_token_ms" in done
    assert "total_latency_ms" in done
    assert done["cached"] is False


def test_pipeline_run_stream_cached(pipeline, mock_redis_client):
    mock_redis_client.get.return_value = b"Cached stream reply"
    events = list(
        pipeline.run_stream(
            query="q",
            session_id="s",
            organization_id="org-1",
        )
    )
    types = [e["type"] for e in events]
    assert types == ["meta", "done"]
    assert events[-1]["reply"] == "Cached stream reply"
    assert events[-1]["cached"] is True


def test_pipeline_run_stream_partial_on_error(pipeline, mock_redis_client):
    mock_redis_client.get.return_value = None
    mock_redis_client.lrange.return_value = []
    with patch.object(
        pipeline.ai, "generate_stream", return_value=iter(["Part"])
    ), patch.object(pipeline.ai, "last_stream_error", True, create=True):
        events = list(
            pipeline.run_stream(
                query="q",
                session_id="s",
                organization_id="org-1",
            )
        )
    types = [e["type"] for e in events]
    assert "error" in types
    done = events[-1]
    assert done["reply"] == "Part"
    assert done["stream_error"] is True
