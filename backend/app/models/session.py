from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, unique=True, index=True)
    org_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chatbot_id = Column(
        Integer,
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    expires_at = Column(DateTime, nullable=True)
