import uuid

from sqlalchemy import JSON, Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JsonType, default=dict, server_default="{}")
    description = Column(Text, default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
