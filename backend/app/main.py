import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter
from app.core.secrets import init_secret_manager

settings = get_settings()

# Initialize secret manager at module load time
# In production, Vault is required. In development, falls back to env vars.
_deployment_env = os.getenv("DEPLOYMENT_ENV", "development")
_require_vault = _deployment_env == "production"
_vault_url = os.getenv("VAULT_ADDR")
_vault_token = os.getenv("VAULT_TOKEN")

init_secret_manager(
    vault_url=_vault_url,
    vault_token=_vault_token,
    env=_deployment_env,
    require_vault=_require_vault,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.logging_config import setup_logging
    setup_logging()
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI Knowledge Infrastructure Platform",
    version="0.4.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Security: Request size limit (10 MB)
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)

# Security: Security headers (CSP, HSTS, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# Tracing
from app.core.tracing import setup_tracing
setup_tracing(app)

# Metrics (/metrics + request metrics middleware + background sampler)
from app.core.metrics import setup_metrics
setup_metrics(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(api_router)


# Health
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "scout-api", "version": "0.4.0"}


@app.get("/health/ready")
async def readiness_check():
    from app.core.health import check_dependencies

    services = check_dependencies()
    all_ok = all(v == "ok" for v in services.values())
    return {"status": "healthy" if all_ok else "degraded", "services": services}
