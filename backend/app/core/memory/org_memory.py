import json

import redis

from app.core.config import get_settings
from app.models import Policy

settings = get_settings()


class OrganizationalMemory:
    def __init__(self, redis_client=None):
        self.client = redis_client or redis.from_url(settings.redis_url)
        self.ttl = 3600

    def _config_key(self, org_id: str) -> str:
        return f"org_config:{org_id}"

    def _policies_key(self, org_id: str) -> str:
        return f"org_policies:{org_id}"

    def cache_config(self, org_id: str, config: dict):
        key = self._config_key(org_id)
        self.client.setex(key, self.ttl, json.dumps(config))

    def get_cached_config(self, org_id: str) -> dict | None:
        key = self._config_key(org_id)
        raw = self.client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def cache_policies(self, org_id: str, policies: list[dict]):
        key = self._policies_key(org_id)
        self.client.setex(key, self.ttl, json.dumps(policies))

    def get_cached_policies(self, org_id: str) -> list[dict] | None:
        key = self._policies_key(org_id)
        raw = self.client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
