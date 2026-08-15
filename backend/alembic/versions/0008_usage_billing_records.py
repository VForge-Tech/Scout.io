"""Add usage_billing_records table

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-15

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_billing_records",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Integer(), nullable=True),
        sa.Column("overage_tokens", sa.Integer(), nullable=True),
        sa.Column("overage_cost", sa.Integer(), nullable=True),
        sa.Column("reported_to_razorpay", sa.Boolean(), nullable=True),
        sa.Column("razorpay_addon_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_usage_billing_org"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "period", name="uq_usage_billing_org_period"
        ),
    )
    op.create_index(
        "ix_usage_billing_records_organization_id",
        "usage_billing_records",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_usage_billing_records_organization_id", table_name="usage_billing_records"
    )
    op.drop_table("usage_billing_records")