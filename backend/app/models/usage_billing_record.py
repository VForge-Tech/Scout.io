import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class UsageBillingRecord(Base):
    """Monthly usage aggregate per organization, written by the billing beat task.

    Tracks how many tokens an org consumed in a billing period, the estimated
    cost, and whether the overage was reported to Razorpay (as a subscription
    add-on) or only tracked internally as a fallback.
    """

    __tablename__ = "usage_billing_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "period", name="uq_usage_billing_org_period"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    period = Column(String(7), nullable=False)  # "YYYY-MM" billing period
    total_tokens = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    estimated_cost = Column(Integer, default=0)  # paise
    overage_tokens = Column(Integer, default=0)
    overage_cost = Column(Integer, default=0)  # paise
    reported_to_razorpay = Column(Boolean, default=False)
    razorpay_addon_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )