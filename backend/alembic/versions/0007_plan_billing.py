"""Add plan and razorpay subscription fields to organizations

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-15

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
    )
    op.add_column(
        "organizations",
        sa.Column("plan_status", sa.String(50), nullable=False, server_default="active"),
    )
    op.add_column(
        "organizations",
        sa.Column("razorpay_customer_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("razorpay_subscription_id", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_organizations_razorpay_customer_id",
        "organizations",
        ["razorpay_customer_id"],
    )
    op.create_index(
        "ix_organizations_razorpay_subscription_id",
        "organizations",
        ["razorpay_subscription_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_organizations_razorpay_subscription_id", table_name="organizations")
    op.drop_index("ix_organizations_razorpay_customer_id", table_name="organizations")
    op.drop_column("organizations", "razorpay_subscription_id")
    op.drop_column("organizations", "razorpay_customer_id")
    op.drop_column("organizations", "plan_status")
    op.drop_column("organizations", "plan")