import logging

import httpx

from app.core.knowledge.connectors.base import BaseKnowledgeConnector, ConnectorConfig
from app.core.knowledge.connectors.registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class APIConnector(BaseKnowledgeConnector):
    connector_type = "api"

    def validate(self, config: ConnectorConfig) -> bool:
        return bool(config.uri)

    def sync(self, config: ConnectorConfig) -> list[tuple[str, dict]]:
        uri = config.uri
        headers = config.config.get("headers", {})
        method = config.config.get("method", "GET").upper()

        if not uri:
            logger.error("API connector missing uri for source %s", config.source_id)
            return []

        try:
            if method == "GET":
                resp = httpx.get(uri, headers=headers, timeout=30)
            elif method == "POST":
                body = config.config.get("body", {})
                resp = httpx.post(uri, headers=headers, json=body, timeout=30)
            else:
                logger.warning("Unsupported API method %s for source %s", method, config.source_id)
                return []

            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list):
                chunks = [(str(item), {"raw": item}) for item in data]
            elif isinstance(data, dict):
                text = "\n".join(f"{k}: {v}" for k, v in data.items())
                chunks = [(text, {"raw": data})]
            else:
                chunks = [(str(data), {"raw": data})]

            return chunks
        except Exception as exc:
            logger.exception("API connector sync failed for source %s: %s", config.source_id, exc)
            return []


ConnectorRegistry.register("api", APIConnector)
