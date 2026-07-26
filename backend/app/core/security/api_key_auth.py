from uuid import UUID

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import ApiKey, Organization, User

security_scheme = HTTPBearer(auto_error=False)


def authenticate_api_key(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    api_key_header = request.headers.get("X-API-Key")
    if not api_key_header:
        return None

    api_keys = db.query(ApiKey).filter(
        ApiKey.is_active.is_(True),
    ).all()

    for key in api_keys:
        try:
            if bcrypt.checkpw(
                api_key_header.encode("utf-8"),
                key.key_hash.encode("utf-8"),
            ):
                key.last_used_at = __import__("datetime").datetime.now()
                db.commit()

                org = db.query(Organization).filter(
                    Organization.id == key.organization_id
                ).first()
                if not org:
                    return None

                user = db.query(User).filter(User.id == key.user_id).first()
                return user
        except Exception:
            continue

    return None
