import json

import redis

from app.core.config import get_settings
from app.models import Policy

settings = get_settings()


class OrganizationalMemory:
    def __init__(self, redis_client=None):
        if not settings.celery_enabled or not settings.redis_url:
            self.client = None
            self.ttl = 3600
            return
            
        self.client = redis_client or redis.from_url(settings.redis_url)
        self.ttl = 3600

    def _config_key(self, org_id: str) -> str:
        return f"org_config:{org_id}"

    def _policies_key(self, org_id: str) -> str:
        return f"org_policies:{org_id}"

    def cache_config(self, org_id: str, config: dict):
        if not self.client:
            return
        key = self._config_key(org_id)
        self.client.setex(key, self.ttl, json.dumps(config))

    def get_cached_config(self, org_id: str) -> dict | None:
        if not self.client:
            return None
        key = self._config_key(org_id)
        raw = self.client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def cache_policies(self, org_id: str, policies: list[dict]):
        if not self.client:
            return
        key = self._policies_key(org_id)
        self.client.setex(key, self.ttl, json.dumps(policies))

    def get_cached_policies(self, org_id: str) -> list[dict] | None:
        if not self.client:
            return None
        key = self._policies_key(org_id)
        raw = self.client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def purge_org(self, org_id: str) -> int:
        """Delete all org config/policies cache keys for an organization."""
        if not self.client:
            return 0
        keys = [self._config_key(org_id), self._policies_key(org_id)]
        return int(self.client.delete(*keys) or 0)
