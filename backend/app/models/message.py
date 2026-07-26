import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text", server_default="text")
    attachments = Column(JsonType, default=list, server_default="[]")
    metadata_ = Column("metadata", JsonType, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
