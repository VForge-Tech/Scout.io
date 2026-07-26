import logging

from app.domain import event_bus
from app.domain.event_bus import DomainEvent

logger = logging.getLogger(__name__)


async def on_knowledge_source_created(event: DomainEvent):
    logger.info("Knowledge source created: %s", event.payload.get("source_id"))


async def on_knowledge_source_synced(event: DomainEvent):
    logger.info("Knowledge source synced: %s", event.payload.get("source_id"))
    logger.info("  chunks indexed: %s", event.payload.get("chunks"))


async def on_message_created(event: DomainEvent):
    logger.info("Message created in session %s", event.payload.get("session_id"))


async def on_analytics_updated(event: DomainEvent):
    logger.info("Analytics updated for org %s", event.payload.get("organization_id"))


def register_domain_handlers():
    event_bus.subscribe("knowledge_source.created", on_knowledge_source_created)
    event_bus.subscribe("knowledge_source.synced", on_knowledge_source_synced)
    event_bus.subscribe("message.created", on_message_created)
    event_bus.subscribe("analytics.updated", on_analytics_updated)
    logger.info("Domain event handlers registered")
