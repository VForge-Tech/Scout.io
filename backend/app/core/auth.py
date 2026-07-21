import logging
import secrets
from datetime import datetime, timedelta

import jwt
import redis
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger("scout_auth")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

try:
    redis_client = redis.from_url(
        settings.REDIS_URL, decode_responses=True, socket_timeout=2.0
    )
except Exception as e:
    logger.error(f"Failed to connect to Redis for auth: {e}")
    redis_client = None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, org_id: int, role: str) -> str:
    expire = datetime.utcnow() + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _generate_fingerprint() -> str:
    return secrets.token_hex(32)


def create_refresh_token(user_id: int, org_id: int, role: str) -> tuple[str, str]:
    fingerprint = _generate_fingerprint()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "type": "refresh",
        "fingerprint": fingerprint,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    if redis_client is not None:
        redis_key = f"refresh_token:{user_id}:{fingerprint}"
        try:
            redis_client.setex(
                redis_key,
                settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                str(org_id),
            )
        except redis.RedisError as e:
            logger.error(f"Redis error storing refresh token: {e}")

    return token, fingerprint


def revoke_refresh_token(user_id: int, fingerprint: str) -> None:
    if redis_client is not None:
        redis_key = f"refresh_token:{user_id}:{fingerprint}"
        try:
            redis_client.delete(redis_key)
        except redis.RedisError as e:
            logger.error(f"Redis error revoking refresh token: {e}")


def validate_refresh_token(user_id: int, fingerprint: str) -> bool:
    if redis_client is None:
        return False
    redis_key = f"refresh_token:{user_id}:{fingerprint}"
    try:
        return redis_client.exists(redis_key) > 0
    except redis.RedisError as e:
        logger.error(f"Redis error validating refresh token: {e}")
        return False


def revoke_all_user_refresh_tokens(user_id: int) -> None:
    if redis_client is not None:
        try:
            cursor = 0
            pattern = f"refresh_token:{user_id}:*"
            while True:
                cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    redis_client.delete(*keys)
                if cursor == 0:
                    break
        except redis.RedisError as e:
            logger.error(f"Redis error revoking all tokens for user {user_id}: {e}")
