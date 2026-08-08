# Scout.io Setup Guide

## Quick Demo (Tests Only — No Infrastructure Required)

Everything can be verified via tests with **zero external services**:

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

**Expected Outcome:** All 85 tests pass (~35 seconds). This covers:
- **Authentication**: JWT login/refresh/logout, protected endpoints
- **Organizations & Users**: CRUD, isolation, role-based access
- **Chatbots**: CRUD, behavior settings (fast/balanced/accurate)
- **Policies**: Source filtering, content filtering, org-level policies
- **Knowledge Sources**: CRUD, connector types (API, SQL, file, web)
- **Widget API**: Session creation, message exchange
- **Admin Endpoints**: Org management, audit logs, platform stats, system health
- **Developer Portal**: API keys, widget snippet generator
- **AI/RAG Pipeline**: Knowledge engine, AI router, memory framework, response pipeline
- **Validation**: Response validation, sanitization, safety checks
- **Analytics**: Event tracking, daily aggregation, chatbot/org/source analytics
- **Multi-modal**: Message types, attachments
- **Feature Flags**: Qdrant, LiteLLM, Celery, pgvector, Ollama toggles

---

## Full Stack Demo with Docker (Recommended)

### Prerequisites
- Docker & Docker Compose
- (Optional) LLM API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.

### 1. Environment Setup

```bash
scripts/setup_env.sh
```

Edit `backend/.env` and add at least one LLM API key:
```env
OPENAI_API_KEY=sk-your-key-here
# or
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 2. Start Infrastructure

**Full Stack (PostgreSQL + Redis + Qdrant + Ollama):**
```bash
docker compose -f docker/docker-compose.yml --profile full up -d
```

**Minimal (PostgreSQL + Redis only, no Qdrant):**
```bash
docker compose -f docker/docker-compose.yml up -d postgres redis
```

**Development with hot-reload:**
```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml --profile full up -d
```

### 3. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

### 4. Start Backend

```bash
cd backend
uv pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Expected Outcome:**
- API running at `http://localhost:8000`
- API docs at `http://localhost:8000/docs`
- Health check: `GET /health` → `{"status": "ok", "service": "scout-api", "version": "0.4.0"}`
- Readiness check: `GET /health/ready` → shows database/redis/qdrant status

### 5. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

**Expected Outcome:**
- Dashboard at `http://localhost:3000`
- Admin pages: `/admin`, `/admin/organizations`, `/admin/audit-logs`, `/admin/system-health`, `/admin/settings`
- Developer pages: `/developer`, `/developer/api-keys`, `/developer/docs`, `/developer/widget`
- Login at `/auth/login`

### 6. Build Widget

```bash
cd widget
npm install
npm run build
```

**Expected Outcome:**
- `dist/scout-widget.js` (UMD bundle)
- `dist/scout-widget.esm.js` (ESM bundle)
- `dist/index.d.ts` (TypeScript definitions)

---

## Local Development (No Docker)

### Backend with SQLite (MVP Demo)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables (PowerShell)
$env:DATABASE_URL="sqlite:///./scout_demo.db"
$env:JWT_SECRET="demo-secret-key-for-mvp"
$env:QDRANT_ENABLED="false"
$env:CELERY_ENABLED="false"
$env:LITELLM_ENABLED="false"
$env:REDIS_URL=""
$env:QDRANT_URL=""

# Run server
uvicorn app.main:app --reload --port 8000
```

**Expected Outcome:**
- API running at `http://localhost:8000`
- All endpoints functional (uses SQLite, in-memory fallbacks)
- No external services required

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Widget

```bash
cd widget
npm install
npm run build
```

---

## Docker Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| (none) | postgres, redis, qdrant, backend | Full production |
| `--profile minimal` | postgres, redis, backend | No Qdrant |
| `--profile ollama` | + ollama | Local LLMs |
| `--profile pgvector` | + pgvector | PostgreSQL vectors |

Configure feature flags in `backend/.env`:
```env
QDRANT_ENABLED=true
OLLAMA_ENABLED=false
PGVECTOR_ENABLED=false
CELERY_ENABLED=true
LITELLM_ENABLED=true
```

---

## API Quickstart

### 1. Create Organization & User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "securepass", "full_name": "Admin", "organization_name": "MyOrg"}'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "securepass"}'
```
→ Returns `access_token` and `refresh_token`

### 3. Create Chatbot
```bash
curl -X POST http://localhost:8000/api/v1/chatbots \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Support Bot", "behaviour": "balanced"}'
```

### 4. Add Knowledge Source
```bash
curl -X POST http://localhost:8000/api/v1/knowledge-sources \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"chatbot_id": "<bot_id>", "source_type": "text", "name": "FAQ", "content": "Our return policy is 30 days..."}'
```

### 5. Create Widget Session
```bash
curl -X POST http://localhost:8000/api/v1/widget/sessions \
  -H "Content-Type: application/json" \
  -d '{"chatbot_id": "<bot_id>", "customer_id": "user-123"}'
```
→ Returns `session_id` and `token`

### 6. Send Message via Widget
```bash
curl -X POST http://localhost:8000/api/v1/widget/messages \
  -H "Authorization: Bearer <widget_token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "What is your return policy?"}'
```
→ Returns AI-generated response

---

## Key Endpoints

| Category | Endpoint | Description |
|----------|----------|-------------|
| Health | `GET /health` | Basic health |
| Health | `GET /health/ready` | Dependency checks |
| Auth | `POST /api/v1/auth/login` | Login |
| Auth | `POST /api/v1/auth/refresh` | Refresh token |
| Auth | `POST /api/v1/auth/logout` | Logout |
| Chatbots | `GET/POST /api/v1/chatbots` | List/Create |
| Chatbots | `GET/PATCH/DELETE /api/v1/chatbots/{id}` | Manage |
| Knowledge | `GET/POST /api/v1/knowledge-sources` | List/Create |
| Widget | `POST /api/v1/widget/sessions` | Create session |
| Widget | `POST /api/v1/widget/messages` | Send message |
| Admin | `GET /api/v1/admin/organizations` | List orgs |
| Admin | `GET /api/v1/admin/audit-logs` | Audit logs |
| Admin | `GET /api/v1/admin/health` | System health |
| Developer | `GET/POST/DELETE /api/v1/developer/api-keys` | API keys |
| Developer | `GET /api/v1/developer/widget-snippet` | Embed code |

---

## Troubleshooting

### Port Conflicts
```bash
# Check what's using ports
netstat -an | findstr "5432 6379 6333 8000 3000"

# Kill process on port (PowerShell)
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess
```

### Docker Issues
```bash
# Restart Docker Desktop
# Then rebuild
docker compose -f docker/docker-compose.yml --profile full up --build -d
```

### Database Issues
```bash
cd backend
alembic downgrade base
alembic upgrade head
```

### Missing LLM Keys
Set in `backend/.env`:
```env
OPENAI_API_KEY=sk-...
# or use local models with Ollama
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.2
```

---

## Expected Test Results

```bash
cd backend
python -m pytest tests/ -v
```

**Output:**
```
============================== test session starts =============================
collected 85 items

tests/test_admin.py .......... [ 10%]
tests/test_ai_router.py ........ [ 20%]
tests/test_auth.py ........... [ 30%]
tests/test_chatbots.py ........ [ 40%]
tests/test_config_flags.py ... [ 43%]
tests/test_connectors.py ....... [ 50%]
tests/test_domain_services.py ... [ 53%]
tests/test_event_bus.py ....... [ 60%]
tests/test_knowledge_engine.py ...... [ 67%]
tests/test_knowledge_source_connector.py ... [ 70%]
tests/test_knowledge_sources.py ... [ 73%]
tests/test_memory.py ........... [ 80%]
tests/test_models.py ........... [ 87%]
tests/test_multimodal.py .. [ 89%]
tests/test_pipeline.py ... [ 92%]
tests/test_policies.py ... [ 95%]
tests/test_validation.py ....... [100%]

====================== 85 passed, 18 warnings in 35.28s =======================
```

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │     │   Widget    │     │   SDKs      │
│  (Next.js)  │     │  (React)    │     │ (Py/JS)     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
              ┌─────────────────────────┐
              │      Backend API        │
              │      (FastAPI)          │
              └───────────┬─────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  PostgreSQL   │ │    Redis      │ │    Qdrant     │
│  (Primary DB) │ │  (Cache/Queue)│ │ (Vector DB)   │
└───────────────┘ └───────────────┘ └───────────────┘
```

---

## Support

- **Documentation**: `/docs` folder
- **API Docs**: `http://localhost:8000/docs`
- **Issues**: GitHub Issues