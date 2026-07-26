import logging

from app.domain import event_bus
from app.domain.event_bus import DomainEvent

logger = logging.getLogger(__name__)


class KnowledgeDomainService:
    def on_source_created(self, source_id: str):
        event_bus.publish_sync(
            DomainEvent(
                event_type="knowledge_source.created",
                payload={"source_id": source_id},
            )
        )

    def on_source_synced(self, source_id: str, chunks: int):
        event_bus.publish_sync(
            DomainEvent(
                event_type="knowledge_source.synced",
                payload={"source_id": source_id, "chunks": chunks},
            )
        )
