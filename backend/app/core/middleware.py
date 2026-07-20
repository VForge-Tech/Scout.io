import logging
import time
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import redis

from app.core.config import settings
from app.core.security import current_org_id_var, verify_token

logger = logging.getLogger("scout_middleware")

# Initialize Redis client for rate limiting
try:
    redis_client = redis.from_url(
        settings.REDIS_URL, decode_responses=True, socket_timeout=2.0
    )
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None


class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Bypass rate limiting for documentation or static health checks
        if request.url.path in ["/healthz", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        # Redis key format: rate_limit:IP:minute_bucket
        minute_bucket = int(time.time() / 60)
        redis_key = f"rate_limit:{client_ip}:{minute_bucket}"

        if redis_client is not None:
            try:
                # Increment request count in current 1-minute window
                pipe = redis_client.pipeline()
                pipe.incr(redis_key)
                pipe.expire(redis_key, 60)
                current_requests, _ = pipe.execute()

                if current_requests > 100:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": "Rate limit exceeded. Maximum 100 requests per minute allowed."
                        },
                        headers={"Retry-After": "60"},
                    )
            except redis.RedisError as e:
                # Log redis error and gracefully degrade (allow traffic)
                logger.error(f"Redis rate limiting error: {e}")

        return await call_next(request)


class OrgIsolationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract Bearer token from header to set org_id context
        auth_header = request.headers.get("Authorization")
        org_id = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decode token to check org_id
                payload = verify_token(token)
                org_id = payload.get("org_id")
            except Exception:
                # Ignore validation issues here; the dependency get_current_org
                # will raise explicit HTTP 401/403 for protected routes.
                pass

        # Set ContextVar for the current execution flow
        token_reset = current_org_id_var.set(org_id)
        try:
            response = await call_next(request)
            return response
        finally:
            current_org_id_var.reset(token_reset)
