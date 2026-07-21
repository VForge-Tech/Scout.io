from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_admin_or_member
from app.api.v1.auth import router as auth_router
from app.core.config import settings
from app.core.db import engine, get_db
from app.core.middleware import OrgIsolationMiddleware, RateLimitingMiddleware
from app.core.security import get_current_org, get_current_user
from app.models.base import Base
from app.models.chatbot import Chatbot
from app.models.user import User

# Create tables (useful for sqlite fallback/in-memory tests)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Scout.io API",
    description="Core backend services for Scout.io organization and chatbot management",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middlewares (Registered in reverse order of execution)
# 1. Tenant context isolation middleware
app.add_middleware(OrgIsolationMiddleware)
# 2. Redis-backed rate limiting middleware
app.add_middleware(RateLimitingMiddleware)

# Include routers
app.include_router(auth_router, prefix="/api/v1")


# Pydantic schemas
class ChatbotCreate(BaseModel):
    name: str
    description: str | None = None


class ChatbotResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    org_id: int
    is_active: bool

    class Config:
        from_attributes = True


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "app": "Scout.io Core API",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# Protected Chatbot CRUD Routes
@app.post(
    "/api/v1/chatbots",
    response_model=ChatbotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chatbot(
    chatbot_in: ChatbotCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_member),
    org_id: int = Depends(get_current_org),
):
    """Creates a chatbot. The org_id is extracted from the JWT token."""
    new_chatbot = Chatbot(
        name=chatbot_in.name,
        description=chatbot_in.description,
        org_id=org_id,
    )
    db.add(new_chatbot)
    db.commit()
    db.refresh(new_chatbot)
    return new_chatbot


@app.get("/api/v1/chatbots", response_model=list[ChatbotResponse])
def list_chatbots(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_member),
    org_id: int = Depends(get_current_org),
):
    """Lists all chatbots. The query is automatically filtered to the current org_id."""
    chatbots = db.query(Chatbot).all()
    return chatbots


@app.get("/api/v1/chatbots/{chatbot_id}", response_model=ChatbotResponse)
def get_chatbot(
    chatbot_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_or_member),
    org_id: int = Depends(get_current_org),
):
    """Gets details of a chatbot. Automatically isolated to the current org_id."""
    chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found or not belonging to this organization",
        )
    return chatbot


@app.delete("/api/v1/chatbots/{chatbot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chatbot(
    chatbot_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    org_id: int = Depends(get_current_org),
):
    """Deletes a chatbot. Only admins can delete."""
    chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found or not belonging to this organization",
        )
    db.delete(chatbot)
    db.commit()
    return
