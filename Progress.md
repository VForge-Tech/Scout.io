# Scout.io Progress Tracker

## Phase I: Foundation Layer [COMPLETED]

### Completed
- Database models: Organization, User, Chatbot, Policy, KnowledgeSource, ChatSession
- JWT authentication (access + refresh tokens) with bcrypt password hashing
- API endpoints: auth (login/refresh/logout), organizations, chatbots CRUD, policies CRUD, knowledge sources CRUD
- Admin endpoints: list orgs, get org, update status, platform stats
- Role-based access control with `require_admin` dependency
- Organization isolation enforced in all queries
- Rate limiting with slowapi
- Celery setup with basic health check task
- Alembic initial migration (0001_initial_schema)
- SQLite test infrastructure with 32 passing tests
- Docker Compose: backend, postgres, redis, qdrant services

### Measures to be taken further
- Next sprint (Phase II) will add ApiKey and AuditLog models, developer portal, admin dashboard, organization dashboard, customer widget, and full Next.js App Router frontend.

---

## Phase II: Core Platform Layer [IN PROGRESS]

### Sprint 1: Backend Models & Schemas

#### Completed
- Added `ApiKey` model: id, user_id, organization_id, name, key_prefix, key_hash, last_used_at, expires_at, is_active
- Added `AuditLog` model: id, user_id, organization_id, action, details (JSONB), ip_address, timestamp
- Added `Message` model: id, session_id, role, content, metadata (JSONB)
- Created Alembic migration 0002 adding api_keys, audit_logs, messages tables
- Created Pydantic schemas for ApiKey, AuditLog, Widget session/request/response
- Created `app/utils/audit.py` helper for logging audit events
- Added `widget_session_token` support via JWT with `type: "widget"` claim
- Created developer endpoints: `POST/DELETE /developer/api-keys`, `GET /developer/api-keys`, `GET /developer/widget-snippet`
- Created widget endpoints: `POST /widget/sessions`, `POST /widget/messages` (with mock responses)
- Enhanced admin endpoints: `PATCH/DELETE /admin/organizations/{id}`, `GET /admin/audit-logs`, `GET /admin/health`
- Updated analytics and sessions endpoints under `/organizations/me/`
- Updated API router to include all new endpoint modules

#### Measures to be taken further
- Next sprint will build the frontend dashboard (Next.js App Router) with route groups for org/admin/developer/auth experiences, plus the widget chat UI.

### Sprint 2: Frontend Dashboard & Widget UI

#### Planned
- Convert Next.js from Pages Router to App Router
- Create route groups: `/(auth)`, `/(org)`, `/(admin)`, `/(developer)`
- Auth pages: login with JWT storage
- Organization Dashboard: sidebar, chatbot CRUD, knowledge sources, policies, analytics, sessions
- Admin Dashboard: organizations list, system health, usage stats, audit logs, settings
- Developer Portal: API key management, widget embed code generator, API docs placeholder
- Widget: real chat UI with message list, input box, theme support
- Integrate React Query for data fetching

---

## Future Phases

### Phase III: AI & RAG Pipeline
- Replace mock responses with real LLM integration via LiteLLM
- Knowledge ingestion: PDF parsing, website crawling, chunking
- Vector embeddings with Qdrant
- Semantic search and RAG query pipeline

### Phase IV: Production Hardening
- Multi-factor authentication
- Webhook system
- Rate limit configuration UI
- Advanced analytics and cost tracking
- Performance optimization
