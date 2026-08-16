from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MfaStatusResponse(BaseModel):
    mfa_enabled: bool


class MfaRequiredResponse(BaseModel):
    mfa_required: bool = True
    mfa_token: str


class MfaSetupRequest(BaseModel):
    password: str


class MfaSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_data_uri: str


class MfaEnableRequest(BaseModel):
    secret: str
    code: str


class MfaEnableResponse(BaseModel):
    mfa_enabled: bool = True
    recovery_codes: list[str]


class MfaDisableRequest(BaseModel):
    password: str
    code: str


class MfaVerifyLoginRequest(BaseModel):
    mfa_token: str
    code: str


class RecoveryCodesRegenerateRequest(BaseModel):
    password: str
    code: str


class RecoveryCodesRegenerateResponse(BaseModel):
    recovery_codes: list[str]
