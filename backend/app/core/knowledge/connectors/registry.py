import logging

from app.core.knowledge.connectors.base import BaseKnowledgeConnector

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    _connectors: dict[str, type[BaseKnowledgeConnector]] = {}

    @classmethod
    def register(cls, connector_type: str, connector_cls: type[BaseKnowledgeConnector]):
        cls._connectors[connector_type] = connector_cls
        logger.debug("Registered connector type=%s", connector_type)

    @classmethod
    def get(cls, connector_type: str) -> type[BaseKnowledgeConnector] | None:
        return cls._connectors.get(connector_type)

    @classmethod
    def list_types(cls) -> list[str]:
        return list(cls._connectors.keys())

    @classmethod
    def get_or_default(cls, connector_type: str) -> type[BaseKnowledgeConnector] | None:
        return cls._connectors.get(connector_type)
