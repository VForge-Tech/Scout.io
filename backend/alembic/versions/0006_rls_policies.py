"""Enable Row-Level Security on all organization-scoped tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-14

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ORG_SCOPED_TABLES = [
    "users",
    "chatbots",
    "policies",
    "knowledge_sources",
    "sessions",
    "messages",
    "api_keys",
    "audit_logs",
    "analytics_events",
    "daily_analytics",
    "llm_usage",
    "webhooks",
]


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def _create_org_policy(table: str) -> None:
    """Create the standard org-isolation policy for SELECT/INSERT/UPDATE/DELETE."""
    op.execute(
        f"""
        CREATE POLICY org_isolation_policy ON {table}
        FOR ALL
        USING (organization_id = current_setting('app.current_org_id')::uuid)
        WITH CHECK (organization_id = current_setting('app.current_org_id')::uuid)
        """
    )


def _create_admin_bypass_policy(table: str) -> None:
    """Create a policy allowing platform admins (role='platform_admin') to bypass RLS.

    This policy only applies when the session variable 'app.is_platform_admin' is set to 'true'.
    Admin endpoints will set this variable before executing cross-org queries.
    """
    op.execute(
        f"""
        CREATE POLICY platform_admin_bypass ON {table}
        FOR ALL
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
        """
    )


def _create_messages_rls() -> None:
    """Messages table doesn't have organization_id directly; it joins through sessions."""
    # Enable RLS on messages
    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY")

    # Policy: user can only see messages in sessions belonging to their organization
    op.execute(
        """
        CREATE POLICY org_isolation_policy ON messages
        FOR ALL
        USING (
            session_id IN (
                SELECT id FROM sessions
                WHERE organization_id = current_setting('app.current_org_id')::uuid
            )
        )
        WITH CHECK (
            session_id IN (
                SELECT id FROM sessions
                WHERE organization_id = current_setting('app.current_org_id')::uuid
            )
        )
        """
    )

    # Admin bypass for messages
    op.execute(
        """
        CREATE POLICY platform_admin_bypass ON messages
        FOR ALL
        USING (current_setting('app.is_platform_admin', true) = 'true')
        WITH CHECK (current_setting('app.is_platform_admin', true) = 'true')
        """
    )


def _drop_org_policy(table: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS org_isolation_policy ON {table}")


def _drop_admin_policy(table: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS platform_admin_bypass ON {table}")


def _disable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    # Create the custom GUCs if they don't exist (they're session-scoped, so just document here)
    # In practice, these are set via SET LOCAL in the application code.

    # Enable RLS and create policies for all org-scoped tables
    for table in ORG_SCOPED_TABLES:
        _enable_rls(table)
        _create_org_policy(table)
        _create_admin_bypass_policy(table)

    # Special handling for messages (no direct org_id)
    _create_messages_rls()


def downgrade() -> None:
    # Drop policies and disable RLS in reverse order
    _drop_admin_policy("messages")
    _drop_org_policy("messages")
    _disable_rls("messages")

    for table in reversed(ORG_SCOPED_TABLES):
        _drop_admin_policy(table)
        _drop_org_policy(table)
        _disable_rls(table)