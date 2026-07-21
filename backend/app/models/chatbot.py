from sqlalchemy import Boolean, Column, Integer, String

from app.models.base import Base


class Chatbot(Base):
    __tablename__ = "chatbots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    org_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
