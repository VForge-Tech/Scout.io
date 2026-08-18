from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_db_admin
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Organization, User
from app.schemas.auth import (
    LoginRequest,
    MfaRequiredResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.utils.audit import create_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
@limiter.limit("10/minute")
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db_admin),
):
    """Create a new organization and its first (admin) user, then auto-login.

    Uses the platform-admin bypass session so the bootstrap rows can be
    inserted under RLS before any org-scoped context exists.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    org = Organization(
        name=payload.organization_name or f"{payload.full_name or payload.email} Org"
    )
    db.add(org)
    db.flush()

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        organization_id=org.id,
        role="admin",
    )
    db.add(user)
    db.flush()

    org_id = org.id
    user_id = user.id
    user_role = user.role

    create_audit_log(
        db, action="user.register", user_id=user_id,
        organization_id=org_id,
        ip_address=request.client.host if request.client else None,
    )

    access_token = create_access_token(
        subject=str(user_id),
        organization_id=org_id,
        extra_claims={"role": user_role},
    )
    refresh_token = create_refresh_token(
        subject=str(user_id),
        organization_id=org_id,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "organization_id": user.organization_id,
        "is_active": user.is_active,
    }


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    if user.mfa_enabled:
        mfa_token = create_access_token(
            subject=str(user.id),
            extra_claims={"type": "mfa_verify"},
        )
        return MfaRequiredResponse(mfa_required=True, mfa_token=mfa_token)

    access_token = create_access_token(
        subject=str(user.id),
        organization_id=user.organization_id,
        extra_claims={"role": user.role},
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        organization_id=user.organization_id,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)
    if token_data is None or token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.query(User).filter(User.id == UUID(token_data["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_access_token(
        subject=str(user.id),
        organization_id=user.organization_id,
        extra_claims={"role": user.role},
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        organization_id=user.organization_id,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)
    if token_data and token_data.get("sub"):
        from app.models import User as UserModel
        user = db.query(UserModel).filter(UserModel.id == UUID(token_data["sub"])).first()
        if user:
            create_audit_log(
                db, action="user.logout", user_id=user.id,
                organization_id=user.organization_id,
                ip_address=request.client.host if request.client else None,
            )
    return None
