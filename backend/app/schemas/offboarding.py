from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OffboardRequest(BaseModel):
    """Request to begin the org-offboarding confirmation flow.

    The requester must be a platform admin. A short-lived signed
    ``confirmation_token`` is returned; it must be echoed back in
    :class:`OffboardConfirm` to execute the purge.
    """


class OffboardConfirm(BaseModel):
    confirmation_token: str


class OffboardPreview(BaseModel):
    organization_id: UUID
    organization_name: str
    postgres: dict
    qdrant: dict
    pgvector: dict | None = None
    redis: dict
    uploads: dict
    vector_store: str | None = None
    confirmation_token: str
    token_expires_minutes: int = 15


class OffboardReport(BaseModel):
    organization_id: UUID
    organization_name: str
    status: str
    deleted: dict
    audit_log_id: str
    retained: dict
    completed_at: datetime