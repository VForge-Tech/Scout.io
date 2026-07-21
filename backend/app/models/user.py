from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="member")
    org_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, default=True)
