from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.models.base import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    org_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chatbot_id = Column(
        Integer,
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    value = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
