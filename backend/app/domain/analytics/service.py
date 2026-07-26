from app.domain import event_bus
from app.domain.event_bus import DomainEvent


class AnalyticsDomainService:
    def record_event(self, organization_id: str, event_type: str, metadata: dict | None = None):
        event_bus.publish_sync(
            DomainEvent(
                event_type="analytics.updated",
                payload={
                    "organization_id": organization_id,
                    "event_type": event_type,
                    "metadata": metadata or {},
                },
            )
        )
