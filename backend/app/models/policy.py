import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    chatbot_id = Column(
        UUID(as_uuid=True), ForeignKey("chatbots.id"), nullable=True
    )
    name = Column(String(255), nullable=False)
    policy_type = Column(String(50), nullable=False)
    rules = Column(JsonType, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization = relationship("Organization", back_populates="policies")
    chatbot = relationship("Chatbot", back_populates="policies")
