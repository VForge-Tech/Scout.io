import hashlib
import json

import redis

from app.core.config import get_settings

settings = get_settings()


class KnowledgeMemory:
    def __init__(self, redis_client=None):
        self.client = redis_client or redis.from_url(settings.redis_url)
        self.ttl = settings.redis_knowledge_cache_ttl

    def _make_key(self, query: str, organization_id: str, chatbot_id: str | None = None) -> str:
        raw = f"{query}:{organization_id}:{chatbot_id or ''}"
        digest = hashlib.md5(raw.encode()).hexdigest()
        return f"knowledge_cache:{digest}"

    def get_cached_chunks(self, query: str, organization_id: str, chatbot_id: str | None = None) -> list[dict] | None:
        key = self._make_key(query, organization_id, chatbot_id)
        raw = self.client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def cache_chunks(self, query: str, organization_id: str, chunks: list[dict], chatbot_id: str | None = None):
        key = self._make_key(query, organization_id, chatbot_id)
        self.client.setex(key, self.ttl, json.dumps(chunks))
