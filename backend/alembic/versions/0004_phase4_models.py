"""Add Phase IV models (analytics, system_config, webhooks)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False, index=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id"),
            nullable=True,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_sources.id"),
            nullable=True,
        ),
        sa.Column("payload", postgresql.JSONB(), default=dict, server_default="{}"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )

    op.create_table(
        "daily_analytics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_sources.id"),
            nullable=True,
        ),
        sa.Column("entity_type", sa.String(50), nullable=False, default="organization"),
        sa.Column("sessions_count", sa.Integer(), default=0),
        sa.Column("messages_count", sa.Integer(), default=0),
        sa.Column("prompt_tokens", sa.Integer(), default=0),
        sa.Column("completion_tokens", sa.Integer(), default=0),
        sa.Column("total_tokens", sa.Integer(), default=0),
        sa.Column("avg_latency_ms", sa.Float(), default=0.0),
        sa.Column("feedback_positive", sa.Integer(), default=0),
        sa.Column("feedback_negative", sa.Integer(), default=0),
        sa.Column("retrieval_count", sa.Integer(), default=0),
        sa.Column("sync_success_count", sa.Integer(), default=0),
        sa.Column("sync_failure_count", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "system_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("value", postgresql.JSONB(), default=dict, server_default="{}"),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("events", sa.String(500), default="sync.completed"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("secret", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("webhooks")
    op.drop_table("system_config")
    op.drop_table("daily_analytics")
    op.drop_table("analytics_events")
