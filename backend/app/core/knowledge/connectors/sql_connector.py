import logging

from app.core.knowledge.connectors.base import BaseKnowledgeConnector, ConnectorConfig
from app.core.knowledge.connectors.registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class SQLConnector(BaseKnowledgeConnector):
    connector_type = "sql"

    def validate(self, config: ConnectorConfig) -> bool:
        return bool(config.config.get("query")) and bool(config.uri)

    def sync(self, config: ConnectorConfig) -> list[tuple[str, dict]]:
        uri = config.uri
        query = config.config.get("query", "")
        limit = config.config.get("limit", 1000)

        if not uri or not query:
            logger.error("SQL connector missing uri or query for source %s", config.source_id)
            return []

        try:
            import sqlalchemy
            engine = sqlalchemy.create_engine(uri)
            with engine.connect() as conn:
                result = conn.execute(sqlalchemy.text(query + f" LIMIT {limit}"))
                chunks = []
                for row in result:
                    text = " | ".join(str(v) for v in row)
                    chunks.append((text, {"row": dict(row._mapping)}))
                return chunks
        except Exception as exc:
            logger.exception("SQL connector sync failed for source %s: %s", config.source_id, exc)
            return []


ConnectorRegistry.register("sql", SQLConnector)
