from unittest.mock import MagicMock

import pytest

from app.core.memory.knowledge_memory import KnowledgeMemory
from app.core.memory.optimization_memory import OptimizationMemory
from app.core.memory.org_memory import OrganizationalMemory
from app.core.memory.session_memory import SessionMemory


@pytest.fixture
def mock_redis_client():
    return MagicMock()


def test_session_memory_add_and_get(mock_redis_client):
    mock_redis_client.lrange.return_value = []
    mem = SessionMemory(redis_client=mock_redis_client)

    mem.add_message("sess1", "user", "Hello")
    assert mock_redis_client.rpush.called
    assert mock_redis_client.expire.called

    mock_redis_client.lrange.return_value = [
        b'{"role": "user", "content": "Hello"}'
    ]
    history = mem.get_history("sess1")
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"


def test_session_memory_build_context(mock_redis_client):
    mock_redis_client.lrange.return_value = [
        b'{"role": "user", "content": "previous question"}',
        b'{"role": "assistant", "content": "previous answer"}',
    ]
    mem = SessionMemory(redis_client=mock_redis_client)
    context = mem.build_context("sess1", "retrieved knowledge context")

    messages = [m for m in context if m["role"] != "system"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_session_memory_clear(mock_redis_client):
    mem = SessionMemory(redis_client=mock_redis_client)
    mem.clear_session("sess1")
    assert mock_redis_client.delete.called


def test_knowledge_memory_cache(mock_redis_client):
    mem = KnowledgeMemory(redis_client=mock_redis_client)
    chunks = [{"text": "test", "score": 0.9}]

    mem.cache_chunks("query", "org1", chunks)
    assert mock_redis_client.setex.called

    import json
    mock_redis_client.get.return_value = json.dumps(chunks).encode()
    cached = mem.get_cached_chunks("query", "org1")
    assert cached == chunks


def test_optimization_memory(mock_redis_client):
    mem = OptimizationMemory(redis_client=mock_redis_client)
    mem.cache_response("test query", "org1", "cached response")
    assert mock_redis_client.setex.called

    mock_redis_client.get.return_value = b"cached response"
    cached = mem.get_cached_response("test query", "org1")
    assert cached == "cached response"


def test_org_memory_config(mock_redis_client):
    mem = OrganizationalMemory(redis_client=mock_redis_client)
    config = {"plan": "enterprise"}
    mem.cache_config("org1", config)
    assert mock_redis_client.setex.called

    import json
    mock_redis_client.get.return_value = json.dumps(config).encode()
    cached = mem.get_cached_config("org1")
    assert cached == config


def test_org_memory_policies(mock_redis_client):
    mem = OrganizationalMemory(redis_client=mock_redis_client)
    policies = [{"name": "test policy", "rules": {}}]
    mem.cache_policies("org1", policies)
    assert mock_redis_client.setex.called

    import json
    mock_redis_client.get.return_value = json.dumps(policies).encode()
    cached = mem.get_cached_policies("org1")
    assert cached == policies
