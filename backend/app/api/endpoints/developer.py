import secrets
import time
from uuid import UUID
from typing import Optional

import bcrypt
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_with_org
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
    db: Session = Depends(get_db_with_org),
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
    db: Session = Depends(get_db_with_org),
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
    db: Session = Depends(get_db_with_org),
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
    db: Session = Depends(get_db_with_org),
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


# =============================================================================
# API TESTING ENDPOINTS
# =============================================================================

class APITestRequest(BaseModel):
    endpoint: str
    method: str = "GET"
    body: Optional[dict] = None
    headers: Optional[dict] = None


class APITestResponse(BaseModel):
    success: bool
    status_code: int
    response_time_ms: float
    response_data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/api-test", response_model=APITestResponse)
async def test_api_endpoint(
    payload: APITestRequest,
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    """Test any internal API endpoint with the user's auth token."""
    settings = get_settings()
    base_url = f"http://localhost:8000/api/v1"
    
    headers = {
        "Authorization": f"Bearer {payload.headers.get('Authorization', '').replace('Bearer ', '')}" if payload.headers and payload.headers.get('Authorization') else "",
        "Content-Type": "application/json",
    }
    
    # Get user's token from request
    auth_header = payload.headers.get('Authorization') if payload.headers else None
    if not auth_header:
        raise HTTPException(status_code=400, detail="Authorization header required")
    
    headers["Authorization"] = auth_header
    
    url = f"{base_url}{payload.endpoint}"
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if payload.method.upper() == "GET":
                resp = await client.get(url, headers=headers)
            elif payload.method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=payload.body)
            elif payload.method.upper() == "PATCH":
                resp = await client.patch(url, headers=headers, json=payload.body)
            elif payload.method.upper() == "DELETE":
                resp = await client.delete(url, headers=headers)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported method: {payload.method}")
            
            response_time = (time.time() - start_time) * 1000
            
            try:
                response_data = resp.json()
            except:
                response_data = {"raw": resp.text}
            
            return APITestResponse(
                success=resp.is_success,
                status_code=resp.status_code,
                response_time_ms=round(response_time, 2),
                response_data=response_data if resp.is_success else None,
                error=None if resp.is_success else response_data.get("detail", "Request failed")
            )
    except httpx.TimeoutException:
        return APITestResponse(
            success=False,
            status_code=408,
            response_time_ms=30000,
            error="Request timeout"
        )
    except Exception as e:
        return APITestResponse(
            success=False,
            status_code=500,
            response_time_ms=(time.time() - start_time) * 1000,
            error=str(e)
        )


class ConnectivityTestResponse(BaseModel):
    service: str
    status: str  # "healthy", "degraded", "unhealthy"
    response_time_ms: Optional[float] = None
    details: Optional[dict] = None
    error: Optional[str] = None


@router.get("/connectivity-test", response_model=list[ConnectivityTestResponse])
async def test_external_connectivity(
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    """Test connectivity to all external services."""
    settings = get_settings()
    results = []
    
    # Test Database
    start = time.time()
    try:
        db.execute(db.bind.text("SELECT 1"))
        results.append(ConnectivityTestResponse(
            service="database",
            status="healthy",
            response_time_ms=round((time.time() - start) * 1000, 2),
            details={"type": "postgresql"}
        ))
    except Exception as e:
        results.append(ConnectivityTestResponse(
            service="database",
            status="unhealthy",
            error=str(e)
        ))
    
    # Test Redis
    start = time.time()
    try:
        import redis
        r = redis.from_url(settings.redis_url, socket_connect_timeout=5)
        r.ping()
        r.close()
        results.append(ConnectivityTestResponse(
            service="redis",
            status="healthy",
            response_time_ms=round((time.time() - start) * 1000, 2),
            details={"url": settings.redis_url.split("@")[-1] if "@" in settings.redis_url else "local"}
        ))
    except Exception as e:
        results.append(ConnectivityTestResponse(
            service="redis",
            status="unhealthy",
            error=str(e)
        ))
    
    # Test Qdrant
    start = time.time()
    try:
        if settings.qdrant_enabled and settings.qdrant_url:
            from qdrant_client import QdrantClient
            client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key if hasattr(settings, 'qdrant_api_key') else None,
                timeout=10
            )
            collections = client.get_collections()
            results.append(ConnectivityTestResponse(
                service="qdrant",
                status="healthy",
                response_time_ms=round((time.time() - start) * 1000, 2),
                details={
                    "collections": len(collections.collections),
                    "collection_names": [c.name for c in collections.collections]
                }
            ))
        else:
            results.append(ConnectivityTestResponse(
                service="qdrant",
                status="disabled",
                details={"reason": "QDRANT_ENABLED=false"}
            ))
    except Exception as e:
        results.append(ConnectivityTestResponse(
            service="qdrant",
            status="unhealthy",
            error=str(e)
        ))
    
    # Test OpenAI
    start = time.time()
    try:
        if settings.openai_api_key:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"}
                )
                if resp.is_success:
                    models = resp.json().get("data", [])
                    results.append(ConnectivityTestResponse(
                        service="openai",
                        status="healthy",
                        response_time_ms=round((time.time() - start) * 1000, 2),
                        details={"available_models": len(models)}
                    ))
                else:
                    results.append(ConnectivityTestResponse(
                        service="openai",
                        status="unhealthy",
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                    ))
        else:
            results.append(ConnectivityTestResponse(
                service="openai",
                status="not_configured",
                details={"reason": "OPENAI_API_KEY not set"}
            ))
    except Exception as e:
        results.append(ConnectivityTestResponse(
            service="openai",
            status="unhealthy",
            error=str(e)
        ))
    
    # Test Anthropic
    start = time.time()
    try:
        if settings.anthropic_api_key:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01"
                    }
                )
                if resp.is_success:
                    results.append(ConnectivityTestResponse(
                        service="anthropic",
                        status="healthy",
                        response_time_ms=round((time.time() - start) * 1000, 2)
                    ))
                else:
                    results.append(ConnectivityTestResponse(
                        service="anthropic",
                        status="unhealthy",
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                    ))
        else:
            results.append(ConnectivityTestResponse(
                service="anthropic",
                status="not_configured",
                details={"reason": "ANTHROPIC_API_KEY not set"}
            ))
    except Exception as e:
        results.append(ConnectivityTestResponse(
            service="anthropic",
            status="unhealthy",
            error=str(e)
        ))
    
    return results


@router.get("/endpoints")
def list_testable_endpoints(
    user: User = Depends(get_current_user),
):
    """List all endpoints available for testing."""
    return {
        "internal": [
            {"method": "GET", "path": "/health", "description": "Basic health check"},
            {"method": "GET", "path": "/health/ready", "description": "Readiness with dependencies"},
            {"method": "GET", "path": "/auth/me", "description": "Get current user"},
            {"method": "GET", "path": "/organizations/me", "description": "Get current organization"},
            {"method": "GET", "path": "/chatbots", "description": "List chatbots"},
            {"method": "POST", "path": "/chatbots", "description": "Create chatbot"},
            {"method": "GET", "path": "/chatbots/{id}", "description": "Get chatbot"},
            {"method": "PATCH", "path": "/chatbots/{id}", "description": "Update chatbot"},
            {"method": "DELETE", "path": "/chatbots/{id}", "description": "Delete chatbot"},
            {"method": "GET", "path": "/knowledge-sources", "description": "List knowledge sources"},
            {"method": "POST", "path": "/knowledge-sources", "description": "Create knowledge source"},
            {"method": "GET", "path": "/knowledge-sources/{id}", "description": "Get knowledge source"},
            {"method": "DELETE", "path": "/knowledge-sources/{id}", "description": "Delete knowledge source"},
            {"method": "POST", "path": "/widget/sessions", "description": "Create widget session"},
            {"method": "POST", "path": "/widget/messages", "description": "Send widget message"},
            {"method": "GET", "path": "/developer/api-keys", "description": "List API keys"},
            {"method": "POST", "path": "/developer/api-keys", "description": "Create API key"},
            {"method": "DELETE", "path": "/developer/api-keys/{id}", "description": "Revoke API key"},
            {"method": "GET", "path": "/developer/widget-snippet", "description": "Get widget embed code"},
            {"method": "GET", "path": "/debug/retrieve", "description": "Debug retrieval"},
        ],
        "admin": [
            {"method": "GET", "path": "/admin/organizations", "description": "List organizations (admin)"},
            {"method": "GET", "path": "/admin/audit-logs", "description": "View audit logs (admin)"},
            {"method": "GET", "path": "/admin/health", "description": "System health (admin)"},
            {"method": "GET", "path": "/admin/stats", "description": "Platform stats (admin)"},
        ]
    }


@router.post("/test-chatbot/{chatbot_id}")
async def test_chatbot_endpoint(
    chatbot_id: UUID,
    message: str = "Hello, can you help me?",
    db: Session = Depends(get_db_with_org),
    user: User = Depends(get_current_user),
):
    """Test a full chatbot interaction via widget API."""
    from app.core.pipeline.response_pipeline import ResponsePipeline
    from app.models import Chatbot, ChatSession, Message, Policy
    
    chatbot = db.query(Chatbot).filter(
        Chatbot.id == chatbot_id,
        Chatbot.organization_id == user.organization_id
    ).first()
    
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    
    # Create a test session
    session = ChatSession(
        organization_id=user.organization_id,
        chatbot_id=chatbot.id,
        customer_id="test-user",
        metadata_={"test": True}
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Get policies
    policies = db.query(Policy).filter(
        Policy.organization_id == user.organization_id,
        (Policy.chatbot_id == chatbot.id) | (Policy.chatbot_id.is_(None))
    ).all()
    
    start = time.time()
    pipeline = ResponsePipeline()
    result = pipeline.run(
        query=message,
        session_id=str(session.id),
        organization_id=str(user.organization_id),
        chatbot_id=str(chatbot.id),
        behaviour=chatbot.behaviour,
        db=db,
        policies=policies,
        reranker_enabled=(
            chatbot.config.get("reranker_enabled") if chatbot.config else None
        ),
    )
    response_time = round((time.time() - start) * 1000, 2)
    
    return {
        "success": True,
        "chatbot_id": str(chatbot.id),
        "chatbot_name": chatbot.name,
        "behaviour": chatbot.behaviour,
        "query": message,
        "response": result["reply"],
        "response_time_ms": response_time,
        "cached": result.get("cached", False),
        "session_id": str(session.id)
    }
