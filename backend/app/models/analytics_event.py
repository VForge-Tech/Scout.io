import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    chatbot_id = Column(
        UUID(as_uuid=True), ForeignKey("chatbots.id"), nullable=True
    )
    source_id = Column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id"), nullable=True
    )
    payload = Column(JsonType, default=dict, server_default="{}")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
