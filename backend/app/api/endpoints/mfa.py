from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_code,
    provisioning_uri,
    qr_data_uri,
    recovery_code_matches,
    verify_password,
    verify_recovery_code,
    verify_totp,
)
from app.models import User
from app.schemas.auth import (
    MfaDisableRequest,
    MfaEnableRequest,
    MfaEnableResponse,
    MfaSetupRequest,
    MfaSetupResponse,
    MfaStatusResponse,
    MfaVerifyLoginRequest,
    RecoveryCodesRegenerateRequest,
    RecoveryCodesRegenerateResponse,
    TokenResponse,
)
from app.utils.audit import create_audit_log

router = APIRouter(prefix="/auth/mfa", tags=["auth", "mfa"])


def _verify_user_code(db: Session, user: User, code: str) -> bool:
    """Verify a TOTP code or one-time recovery code, consuming the recovery code if used."""
    if user.totp_secret and verify_totp(decrypt_totp_secret(user.totp_secret), code):
        return True
    if user.recovery_codes and verify_recovery_code(code, user.recovery_codes):
        user.recovery_codes = [
            stored for stored in user.recovery_codes
            if not recovery_code_matches(code, stored)
        ]
        db.commit()
        return True
    return False


def _issue_tokens(user: User) -> TokenResponse:
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


@router.get("/status", response_model=MfaStatusResponse)
def get_mfa_status(user: User = Depends(get_current_user)):
    return MfaStatusResponse(mfa_enabled=user.mfa_enabled)


@router.post("/setup", response_model=MfaSetupResponse)
def setup_mfa(
    payload: MfaSetupRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    if user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    secret = generate_totp_secret()
    uri = provisioning_uri(secret, user.email)
    create_audit_log(
        db, action="mfa.setup_initiated", user_id=user.id,
        organization_id=user.organization_id,
        ip_address=request.client.host if request.client else None,
    )
    return MfaSetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_data_uri=qr_data_uri(uri),
    )


@router.post("/enable", response_model=MfaEnableResponse)
def enable_mfa(
    payload: MfaEnableRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_totp(payload.secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )
    if user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    user.totp_secret = encrypt_totp_secret(payload.secret)
    recovery_codes = generate_recovery_codes()
    user.recovery_codes = [hash_recovery_code(code) for code in recovery_codes]
    user.mfa_enabled = True
    db.commit()
    db.refresh(user)
    create_audit_log(
        db, action="mfa.enabled", user_id=user.id,
        organization_id=user.organization_id,
        ip_address=request.client.host if request.client else None,
    )
    return MfaEnableResponse(recovery_codes=recovery_codes)


@router.post("/disable", status_code=status.HTTP_204_NO_CONTENT)
def disable_mfa(
    payload: MfaDisableRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    if not _verify_user_code(db, user, payload.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication code",
        )

    user.totp_secret = None
    user.recovery_codes = None
    user.mfa_enabled = False
    db.commit()
    create_audit_log(
        db, action="mfa.disabled", user_id=user.id,
        organization_id=user.organization_id,
        ip_address=request.client.host if request.client else None,
    )
    return None


@router.post("/recovery-codes/regenerate", response_model=RecoveryCodesRegenerateResponse)
def regenerate_recovery_codes(
    payload: RecoveryCodesRegenerateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    if not _verify_user_code(db, user, payload.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication code",
        )

    recovery_codes = generate_recovery_codes()
    user.recovery_codes = [hash_recovery_code(code) for code in recovery_codes]
    db.commit()
    create_audit_log(
        db, action="mfa.recovery_codes_regenerated", user_id=user.id,
        organization_id=user.organization_id,
        ip_address=request.client.host if request.client else None,
    )
    return RecoveryCodesRegenerateResponse(recovery_codes=recovery_codes)


@router.post("/verify-login", response_model=TokenResponse)
def verify_login(
    payload: MfaVerifyLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    token_data = decode_token(payload.mfa_token)
    if token_data is None or token_data.get("type") != "mfa_verify":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        )
    user = db.query(User).filter(User.id == UUID(token_data["sub"])).first()
    if user is None or not user.is_active or not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    if not _verify_user_code(db, user, payload.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication code",
        )
    create_audit_log(
        db, action="user.login", user_id=user.id,
        organization_id=user.organization_id,
        ip_address=request.client.host if request.client else None,
    )
    return _issue_tokens(user)