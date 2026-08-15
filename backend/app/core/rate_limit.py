"""Rate limiting setup.

The Limiter instance lives here (not in app.main) so API endpoint modules can
import it without creating a circular dependency (app.main imports the routers,
which would otherwise import app.main).

Default key function is remote IP (SlowAPIMiddleware default). The widget
message endpoint additionally applies a per-organization limit keyed on the
widget token's org claim, so one org's traffic can't starve another's.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import decode_token

limiter = Limiter(key_func=get_remote_address)


def widget_org_key(request: Request) -> str:
    """Key function that rate-limits widget traffic per organization.

    Extracts the org_id from the widget session token in the Authorization
    header. Falls back to the remote address when the token is missing or
    unparseable (so unauthenticated callers are still bounded by IP).
    """
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()
    if token:
        payload = decode_token(token)
        org_id = (payload or {}).get("org_id")
        if org_id:
            return f"org:{org_id}"
    return get_remote_address(request)