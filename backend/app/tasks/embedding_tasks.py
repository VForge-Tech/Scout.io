import logging
from uuid import UUID

from celery import Celery

from app.core.config import get_settings
from app.core.metrics import register_celery_metrics

settings = get_settings()
register_celery_metrics()

celery_app = Celery(
    "scout",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    broker_connection_retry_on_startup=False,
)

celery_app.conf.broker_connection_timeout = 2
celery_app.conf.result_backend_timeout = 2

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_knowledge_source(self, source_id: str):
    from app.db.session import SessionLocal
    from app.models import KnowledgeSource
    from app.core.knowledge.embeddings import EmbeddingService
    from app.core.knowledge.qdrant_store import QdrantStore
    from app.core.knowledge.engine import KnowledgeEngine
    from app.core.knowledge.connectors import ConnectorRegistry, ConnectorConfig

    db = SessionLocal()
    try:
        source = db.query(KnowledgeSource).filter(
            KnowledgeSource.id == UUID(source_id)
        ).first()
        if not source:
            logger.error("Knowledge source %s not found", source_id)
            return {"status": "error", "message": "Source not found"}

        source.sync_status = "processing"
        db.commit()

        chunks = _parse_and_chunk(source)
        if not chunks:
            source.sync_status = "completed"
            source.last_sync_at = __import__("datetime").datetime.now()
            db.commit()
            return {"status": "completed", "chunks": 0}

        engine = KnowledgeEngine(
            qdrant_store=QdrantStore(),
            embedding_service=EmbeddingService(),
        )

        metadata = {
            "source_id": str(source.id),
            "organization_id": str(source.organization_id),
            "chatbot_id": str(source.chatbot_id) if source.chatbot_id else "",
            "source_type": source.source_type,
            "uri": source.uri,
        }

        enriched_chunks = [
            (text, {**metadata, "chunk_index": i})
            for i, (text, _) in enumerate(chunks)
        ]

        engine.index_chunks(enriched_chunks)

        source.sync_status = "completed"
        source.last_sync_at = __import__("datetime").datetime.now()
        db.commit()

        return {"status": "completed", "chunks": len(chunks)}

    except Exception as exc:
        logger.exception("Failed to process knowledge source %s", source_id)
        source = db.query(KnowledgeSource).filter(
            KnowledgeSource.id == UUID(source_id)
        ).first()
        if source:
            source.sync_status = "failed"
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


def _parse_and_chunk(source) -> list[tuple[str, dict]]:
    from app.core.knowledge.connectors import ConnectorRegistry, ConnectorConfig

    connector_type = (source.config or {}).get("_connector_type")
    if connector_type:
        connector_cls = ConnectorRegistry.get(connector_type)
        if connector_cls:
            config = ConnectorConfig(
                source_id=source.id,
                organization_id=source.organization_id,
                chatbot_id=source.chatbot_id,
                source_type=source.source_type,
                connector_type=connector_type,
                uri=source.uri,
                config=source.config or {},
            )
            return connector_cls().sync(config)
        logger.warning("Unknown connector type %s, falling back to default parsing", connector_type)

    content = source.uri

    if source.source_type == "url":
        try:
            import httpx
            resp = httpx.get(source.uri, timeout=30)
            resp.raise_for_status()
            content = resp.text
        except Exception as e:
            logger.error("Failed to fetch URL %s: %s", source.uri, e)
            return []

    max_chunk_size = 1000
    overlap = 100
    words = content.split()
    chunks = []

    for i in range(0, len(words), max_chunk_size - overlap):
        chunk_words = words[i:i + max_chunk_size]
        if len(chunk_words) < 50 and chunks:
            continue
        chunk_text = " ".join(chunk_words)
        chunks.append((chunk_text, {"chunk_index": len(chunks)}))

    return chunks if chunks else [(content[:1000], {"chunk_index": 0})]


@celery_app.task
def reindex_organization(organization_id: str):
    from app.db.session import SessionLocal
    from app.models import KnowledgeSource

    db = SessionLocal()
    try:
        sources = db.query(KnowledgeSource).filter(
            KnowledgeSource.organization_id == UUID(organization_id)
        ).all()

        results = []
        for source in sources:
            result = process_knowledge_source.delay(str(source.id))
            results.append({"source_id": str(source.id), "task_id": result.id})

        return {"status": "dispatched", "tasks": results}
    finally:
        db.close()
