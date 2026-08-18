"""Add streaming latency columns to llm_usage

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-18

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "llm_usage",
        sa.Column("time_to_first_token_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "llm_usage",
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("llm_usage", "total_latency_ms")
    op.drop_column("llm_usage", "time_to_first_token_ms")