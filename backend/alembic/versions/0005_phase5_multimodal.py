"""Add message_type and attachments to messages

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-26

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.add_column(
        "messages",
        sa.Column("message_type", sa.String(50), server_default="text", nullable=False),
    )
    op.add_column(
        "messages",
        sa.Column("attachments", JSONB, server_default="[]", nullable=False),
    )


def downgrade():
    op.drop_column("messages", "attachments")
    op.drop_column("messages", "message_type")
