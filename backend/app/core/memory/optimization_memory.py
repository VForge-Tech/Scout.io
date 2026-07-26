import hashlib
import json

import redis

from app.core.config import get_settings

settings = get_settings()


class OptimizationMemory:
    def __init__(self, redis_client=None):
        self.client = redis_client or redis.from_url(settings.redis_url)
        self.ttl = settings.redis_optimization_cache_ttl

    def _make_key(self, query: str, org_id: str) -> str:
        raw = f"{query}:{org_id}".lower().strip()
        return f"opt_cache:{hashlib.md5(raw.encode()).hexdigest()}"

    def get_cached_response(self, query: str, org_id: str) -> str | None:
        key = self._make_key(query, org_id)
        raw = self.client.get(key)
        if raw:
            try:
                return raw.decode()
            except (UnicodeDecodeError, AttributeError):
                return None
        return None

    def cache_response(self, query: str, org_id: str, response: str):
        key = self._make_key(query, org_id)
        self.client.setex(key, self.ttl, response)

    def invalidate_org_cache(self, org_id: str):
        cursor = 0
        pattern = f"opt_cache:*"
        while True:
            cursor, keys = self.client.scan(cursor, match=pattern, count=100)
            if keys:
                org_keys = [k for k in keys if f":{org_id}" in k.decode() or True]
                if org_keys:
                    self.client.delete(*org_keys)
            if cursor == 0:
                break
