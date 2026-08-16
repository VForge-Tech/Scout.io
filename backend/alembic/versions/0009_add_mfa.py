"""Add MFA (TOTP) fields to users

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("totp_secret", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column("recovery_codes", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "recovery_codes")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "totp_secret")