import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class ChatSession(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    chatbot_id = Column(
        UUID(as_uuid=True), ForeignKey("chatbots.id"), nullable=False
    )
    customer_id = Column(String, nullable=True)
    started_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JsonType, default=dict, server_default="{}")

    organization = relationship("Organization")
    chatbot = relationship("Chatbot", back_populates="sessions")
