import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class Chatbot(Base):
    __tablename__ = "chatbots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    behaviour = Column(String(50), default="balanced")
    config = Column(JsonType, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization = relationship("Organization", back_populates="chatbots")
    policies = relationship("Policy", back_populates="chatbot", cascade="all, delete-orphan")
    knowledge_sources = relationship(
        "KnowledgeSource", back_populates="chatbot", cascade="all, delete-orphan"
    )
    sessions = relationship("ChatSession", back_populates="chatbot", cascade="all, delete-orphan")
