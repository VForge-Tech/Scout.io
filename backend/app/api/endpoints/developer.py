import secrets
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import ApiKey, Chatbot, Organization, User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead

router = APIRouter(prefix="/developer", tags=["developer"])

API_KEY_PREFIX = "sco_"


def _generate_api_key() -> tuple[str, str, str]:
    raw = secrets.token_hex(32)
    full_key = f"{API_KEY_PREFIX}{raw}"
    prefix = full_key[:8]
    hashed = bcrypt.hashpw(full_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return full_key, prefix, hashed


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from datetime import datetime, timedelta, timezone

    full_key, prefix, key_hash = _generate_api_key()
    expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

    api_key = ApiKey(
        user_id=user.id,
        organization_id=user.organization_id,
        name=payload.name,
        key_prefix=prefix,
        key_hash=key_hash,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        full_key=full_key,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get("/api-keys", response_model=list[ApiKeyRead])
def list_api_keys(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(ApiKey)
        .filter(
            ApiKey.organization_id == user.organization_id,
            ApiKey.is_active.is_(True),
        )
        .all()
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    key = (
        db.query(ApiKey)
        .filter(
            ApiKey.id == key_id,
            ApiKey.organization_id == user.organization_id,
        )
        .first()
    )
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    key.is_active = False
    db.commit()
    return None


@router.get("/widget-snippet")
def get_widget_snippet(
    chatbot_id: str | None = None,
    theme: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if chatbot_id:
        chatbot = (
            db.query(Chatbot)
            .filter(
                Chatbot.id == chatbot_id,
                Chatbot.organization_id == user.organization_id,
            )
            .first()
        )
        if not chatbot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot not found",
            )

    api_url = get_settings().app_name
    theme_config = theme or "light"

    snippet = f"""<!-- Scout.io Chat Widget -->
<script src="https://cdn.scout.io/widget/v1/scout-widget.js" defer></script>
<script>
  window.addEventListener('load', function() {{
    ScoutWidget.init({{
      chatbotId: '{chatbot_id or "YOUR_CHATBOT_ID"}',
      apiUrl: '{api_url}',
      theme: '{theme_config}'
    }});
  }});
</script>"""

    return {"snippet": snippet, "chatbot_id": chatbot_id, "theme": theme_config}
