import uuid

from sqlalchemy import JSON, Column, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class DailyAnalytics(Base):
    __tablename__ = "daily_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False, index=True)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    chatbot_id = Column(
        UUID(as_uuid=True), ForeignKey("chatbots.id"), nullable=True, index=True
    )
    source_id = Column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id"), nullable=True
    )
    entity_type = Column(String(50), nullable=False, default="organization")

    sessions_count = Column(Integer, default=0)
    messages_count = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    feedback_positive = Column(Integer, default=0)
    feedback_negative = Column(Integer, default=0)

    retrieval_count = Column(Integer, default=0)
    sync_success_count = Column(Integer, default=0)
    sync_failure_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
