"""TOTP MFA helpers: secret generation, provisioning URI, QR image, at-rest
encryption, and one-time recovery codes."""

import base64
import hashlib
import io
import secrets
import string

import pyotp
import qrcode

from app.core.config import get_settings
from app.core.security.auth import hash_password, verify_password

RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_ALPHABET = string.ascii_uppercase + string.digits
RECOVERY_CODE_LENGTH = 16  # 4 groups of 4 (XXXX-XXXX-XXXX-XXXX)
RECOVERY_CODE_GROUPS = 4
RECOVERY_CODE_GROUP_SIZE = 4


def _fernet_key() -> bytes:
    """Derive a stable 32-byte URL-safe key for TOTP secret encryption."""
    digest = hashlib.sha256(get_settings().jwt_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email, issuer_name="Scout.io"
    )


def verify_totp(secret: str, code: str) -> bool:
    if not code:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def encrypt_totp_secret(secret: str) -> str:
    from cryptography.fernet import Fernet

    return Fernet(_fernet_key()).encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_totp_secret(stored: str) -> str:
    from cryptography.fernet import Fernet

    return Fernet(_fernet_key()).decrypt(stored.encode("utf-8")).decode("utf-8")


def qr_data_uri(uri: str) -> str:
    img = qrcode.make(uri, box_size=8, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _new_recovery_code() -> str:
    chars = "".join(secrets.choice(RECOVERY_CODE_ALPHABET) for _ in range(RECOVERY_CODE_LENGTH))
    return "-".join(
        chars[i : i + RECOVERY_CODE_GROUP_SIZE]
        for i in range(0, RECOVERY_CODE_LENGTH, RECOVERY_CODE_GROUP_SIZE)
    )


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    return [_new_recovery_code() for _ in range(count)]


def hash_recovery_code(code: str) -> str:
    return hash_password(code)


def _normalize_recovery_code(code: str) -> str:
    normalized = code.strip().upper()
    if "-" not in normalized and len(normalized) == RECOVERY_CODE_LENGTH:
        normalized = "-".join(
            normalized[i : i + RECOVERY_CODE_GROUP_SIZE]
            for i in range(0, RECOVERY_CODE_LENGTH, RECOVERY_CODE_GROUP_SIZE)
        )
    return normalized


def verify_recovery_code(code: str, stored_hashes: list[str] | None) -> bool:
    if not stored_hashes:
        return False
    normalized = _normalize_recovery_code(code)
    return any(verify_password(normalized, stored) for stored in stored_hashes)


def recovery_code_matches(code: str, stored_hash: str) -> bool:
    return verify_password(_normalize_recovery_code(code), stored_hash)