import hashlib
import json

import redis

from app.core.config import get_settings

settings = get_settings()


class OptimizationMemory:
    def __init__(self, redis_client=None):
        if not settings.celery_enabled or not settings.redis_url:
            self.client = None
            self.ttl = settings.redis_optimization_cache_ttl
            return
            
        self.client = redis_client or redis.from_url(settings.redis_url)
        self.ttl = settings.redis_optimization_cache_ttl

    def _make_key(self, query: str, org_id: str) -> str:
        raw = f"{query}:{org_id}".lower().strip()
        return f"opt_cache:{hashlib.md5(raw.encode()).hexdigest()}"

    def get_cached_response(self, query: str, org_id: str) -> str | None:
        if not self.client:
            return None
        key = self._make_key(query, org_id)
        raw = self.client.get(key)
        if raw:
            try:
                return raw.decode()
            except (UnicodeDecodeError, AttributeError):
                return None
        return None

    def cache_response(self, query: str, org_id: str, response: str):
        if not self.client:
            return
        key = self._make_key(query, org_id)
        self.client.setex(key, self.ttl, response)

    def invalidate_org_cache(self, org_id: str):
        """Drop optimization-response cache entries for an organization.

        Keys are md5-hashed (`opt_cache:<md5(query:org)>`) so they cannot be
        matched by prefix. Each cached value embeds no org marker either, so the
        only correct purge is to scan and compare the key's md5 against the
        org-scoped key derivation -- which requires re-deriving every key from
        an unknown query. Instead we evict the whole `opt_cache:*` namespace:
        it is a short-TTL, recomputable cache, so eviction is safe (only a
        transient warm-up cost for the remaining orgs)."""
        if not self.client:
            return
        cursor = 0
        pattern = "opt_cache:*"
        while True:
            cursor, keys = self.client.scan(cursor, match=pattern, count=100)
            if keys:
                self.client.delete(*keys)
            if cursor == 0:
                break
