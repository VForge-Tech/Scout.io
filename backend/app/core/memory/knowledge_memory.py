import hashlib
import json

import redis

from app.core.config import get_settings

settings = get_settings()


class KnowledgeMemory:
    def __init__(self, redis_client=None):
        if not settings.celery_enabled or not settings.redis_url:
            self.client = None
            self.ttl = settings.redis_knowledge_cache_ttl
            return
            
        self.client = redis_client or redis.from_url(settings.redis_url)
        self.ttl = settings.redis_knowledge_cache_ttl

    def _make_key(self, query: str, organization_id: str, chatbot_id: str | None = None) -> str:
        raw = f"{query}:{organization_id}:{chatbot_id or ''}"
        digest = hashlib.md5(raw.encode()).hexdigest()
        return f"knowledge_cache:{digest}"

    def get_cached_chunks(self, query: str, organization_id: str, chatbot_id: str | None = None) -> list[dict] | None:
        if not self.client:
            return None
        key = self._make_key(query, organization_id, chatbot_id)
        raw = self.client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def cache_chunks(self, query: str, organization_id: str, chunks: list[dict], chatbot_id: str | None = None):
        if not self.client:
            return
        key = self._make_key(query, organization_id, chatbot_id)
        self.client.setex(key, self.ttl, json.dumps(chunks))

    def purge_org(self, organization_id: str) -> int:
        """Scan the knowledge cache and drop entries whose chunk metadata belongs
        to the organization. Keys are md5-hashed (not org-prefixed), so entries
        are matched by inspecting each cached payload for the org id."""
        if not self.client:
            return 0
        deleted = 0
        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor=cursor, match="knowledge_cache:*", count=200)
            for key in keys:
                raw = self.client.get(key)
                if not raw:
                    continue
                try:
                    chunks = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                if any(
                    str(c.get("metadata", {}).get("organization_id", "")).lower()
                    == str(organization_id).lower()
                    for c in chunks
                ):
                    self.client.delete(key)
                    deleted += 1
            if cursor == 0:
                break
        return deleted
