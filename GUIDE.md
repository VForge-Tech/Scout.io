# Scout.io Complete Implementation Guide

## Overview

Scout.io is an AI Knowledge Infrastructure Platform that enables organizations to build, deploy, and manage AI-powered chatbots with RAG (Retrieval-Augmented Generation) capabilities.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SCOUT.IO ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Frontend   │    │    Widget    │    │    SDKs      │                  │
│  │  (Next.js)   │    │  (React)     │    │  (Py/JS)     │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                          │
│         └───────────────────┼───────────────────┘                          │
│                             ▼                                              │
│              ┌─────────────────────────┐                                  │
│              │      Backend API        │                                  │
│              │      (FastAPI)          │                                  │
│              └───────────┬─────────────┘                                  │
│                          │                                                │
│         ┌────────────────┼────────────────┐                              │
│         ▼                ▼                ▼                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                        │
│  │ PostgreSQL  │ │    Redis    │ │   Qdrant    │                        │
│  │  (Primary)  │ │ (Cache/Queue)│ │ (Vector DB) │                        │
│  └─────────────┘ └─────────────┘ └─────────────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Server-Side Setup (Developer/Admin)](#server-side-setup-developeradmin)
3. [Client-Side Integration](#client-side-integration)
4. [End-User Workflow](#end-user-workflow)
5. [Environment Configuration](#environment-configuration)
6. [API Reference](#api-reference)
7. [Storage Management](#storage-management)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 20+ | Frontend/Widget build |
| Docker & Docker Compose | Latest | Infrastructure |
| uv | Latest | Python package manager |

### One-Command Demo (No Infrastructure)

```bash
# Backend tests only - zero external dependencies
cd backend
python -m pytest tests/ -v --tb=short
# Expected: 85 passed
```

### Full Stack with Docker (Recommended)

```bash
# 1. Clone and setup environment
git clone <repo>
cd Scout.io
scripts/setup_env.sh

# 2. Configure .env files (see Environment Configuration)
# Edit backend/.env with your credentials

# 3. Start infrastructure
docker compose -f docker/docker-compose.yml --profile full up -d

# 4. Run migrations
cd backend
alembic upgrade head

# 5. Start backend
uv pip install -r requirements.txt
uvicorn app.main:app --reload

# 6. Start frontend
cd ../frontend
npm install
npm run dev
```

**Access Points:**
- Frontend Dashboard: http://localhost:3000 (or 3001)
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- API Testing: http://localhost:3001/developer/api-test

---

## Server-Side Setup (Developer/Admin)

### 1. Developer Workflow

#### Initial Setup

```bash
# Navigate to backend
cd backend

# Install dependencies
uv pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials (see Environment Configuration)

# Initialize database
alembic upgrade head

# Run tests
python -m pytest tests/ -v

# Start development server
uvicorn app.main:app --reload --port 8000
```

#### Developer Portal Features

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/developer` | Overview & quick actions |
| API Keys | `/developer/api-keys` | Create/revoke API keys |
| API Docs | `/developer/docs` | Interactive API documentation |
| Widget Integration | `/developer/widget` | Generate embed code |
| **API Testing** | `/developer/api-test` | **Test all endpoints** |

#### API Testing Workflow (New!)

1. Navigate to `/developer/api-test`
2. **Internal APIs Tab**: Click any endpoint to test with your auth
3. **External Connectivity Tab**: Click "Run Connectivity Test" to verify:
   - Database (PostgreSQL)
   - Redis
   - Qdrant
   - OpenAI API
   - Anthropic API
4. **Chatbot Test Tab**: Select chatbot, enter message, see full pipeline response

```bash
# Example: Test chatbot via API
curl -X POST http://localhost:8000/api/v1/developer/test-chatbot/{chatbot_id} \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what can you do?"}'
```

### 2. Admin Workflow

#### Admin Portal Features

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/admin` | Platform statistics |
| Organizations | `/admin/organizations` | List/suspend organizations |
| Audit Logs | `/admin/audit-logs` | Paginated audit trail |
| System Health | `/admin/system-health` | Real-time service status |
| Settings | `/admin/settings` | System configuration |

#### Admin API Endpoints

```bash
# List organizations (admin only)
GET /api/v1/admin/organizations

# Get platform stats
GET /api/v1/admin/stats

# View audit logs
GET /api/v1/admin/audit-logs?limit=50&offset=0

# System health check
GET /api/v1/admin/health

# Update system config
PUT /api/v1/admin/system-config/{key}
```

#### Organization Management

```bash
# Suspend organization
PATCH /api/v1/admin/organizations/{org_id}
Authorization: Bearer {admin_token}
Content-Type: application/json
{"suspended": true}

# Delete organization
DELETE /api/v1/admin/organizations/{org_id}
```

### 3. Backend Services

#### Core Services

| Service | Module | Purpose |
|---------|--------|---------|
| Auth | `app.api.endpoints.auth` | JWT login/refresh/logout |
| Chatbots | `app.api.endpoints.chatbots` | CRUD + behavior settings |
| Knowledge | `app.api.endpoints.knowledge_sources` | Source management |
| Policies | `app.api.endpoints.policies` | Access control |
| Widget | `app.api.endpoints.widget_api` | Session + message handling |
| Analytics | `app.api.endpoints.analytics` | Event tracking + aggregation |
| Admin | `app.api.endpoints.admin` | Platform management |
| Developer | `app.api.endpoints.developer` | API keys, widget snippet, testing |

#### Background Tasks (Celery)

```bash
# Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Start Celery beat (scheduled tasks)
celery -A app.celery_app beat --loglevel=info
```

**Scheduled Tasks:**
- Daily analytics aggregation (runs at midnight)
- Health checks

#### Knowledge Engine Pipeline

```
User Query → Cache Check → Knowledge Retrieval → Context Optimization 
    → AI Generation → Validation → Sanitization → Cache → Response
```

---

## Client-Side Integration

> **Detailed client integration guide: [ClientREADME.md](./ClientREADME.md)**

### Quick Embed

```html
<!-- Add before </body> -->
<script src="https://cdn.scout.io/widget/v1/scout-widget.js" defer></script>
<script>
  window.addEventListener('load', function() {
    ScoutWidget.init({
      chatbotId: 'YOUR_CHATBOT_ID',
      apiUrl: 'https://your-scout-instance.com',
      theme: 'light'
    });
  });
</script>
```

### NPM Package (React/Next.js/Vue)

```bash
npm install @scout-io/widget
```

```tsx
import { ChatWidget, ThemeProvider } from '@scout-io/widget';
import '@scout-io/widget/styles.css';

function App() {
  return (
    <ThemeProvider theme="light">
      <ChatWidget
        chatbotId="YOUR_CHATBOT_ID"
        apiUrl="https://your-scout-instance.com"
        onMessage={(msg) => console.log('User:', msg)}
        onResponse={(resp) => console.log('Bot:', resp)}
      />
    </ThemeProvider>
  );
}
```

### Widget Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `chatbotId` | string | **Required** | Your chatbot ID |
| `apiUrl` | string | **Required** | Backend API URL |
| `theme` | `'light' \| 'dark'` | `'light'` | Theme |
| `position` | `'bottom-right' \| 'bottom-left'` | `'bottom-right'` | Position |
| `primaryColor` | string | `'#2563eb'` | Brand color |
| `welcomeMessage` | string | `'Hello! How can I help?'` | Initial message |

---

## End-User Workflow

### 1. Organization Onboarding

```
┌─────────────────────────────────────────────────────────────────┐
│                    END-USER JOURNEY                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. SIGN UP                  2. CREATE CHATBOT                 │
│     ┌─────────────┐             ┌─────────────┐                │
│     │ Email/Pass  │────────────▶│ Name + Type │                │
│     │ Org Name    │             │ Behavior    │                │
│     └─────────────┘             └─────────────┘                │
│           │                           │                         │
│           ▼                           ▼                         │
│  3. ADD KNOWLEDGE           4. TEST CHATBOT                    │
│     ┌─────────────┐             ┌─────────────┐                │
│     │ Upload Docs │────────────▶│ Chat in UI  │                │
│     │ URLs/APIs   │             │ /widget-test│                │
│     └─────────────┘             └─────────────┘                │
│           │                           │                         │
│           ▼                           ▼                         │
│  5. EMBED WIDGET           6. GO LIVE                            │
│     ┌─────────────┐             ┌─────────────┐                │
│     │ Copy Snippet│────────────▶│ Paste on    │                │
│     │ Configure   │             │ Website     │                │
│     └─────────────┘             └─────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Knowledge Source Types

| Type | Connector | Use Case |
|------|-----------|----------|
| Text | Built-in | FAQ, policies, manuals |
| File | Built-in | PDF, DOCX, TXT upload |
| Web | Web Connector | Scrape websites |
| API | API Connector | REST/GraphQL endpoints |
| SQL | SQL Connector | Database queries |
| Git | Git Connector | Repository docs |

### 3. Chatbot Behaviors

| Behavior | Model | Use Case |
|----------|-------|----------|
| `fast` | GPT-3.5-Turbo | Quick responses, cost-effective |
| `balanced` | GPT-4o-mini | Best balance (default) |
| `accurate` | GPT-4o | Complex reasoning, highest quality |

### 4. Policies

```json
// Source Filter - restrict knowledge sources
{
  "policy_type": "source_filter",
  "rules": {
    "allowed_source_ids": ["src_123", "src_456"]
  }
}

// Content Filter - block sensitive terms
{
  "policy_type": "content_filter",
  "rules": {
    "blocked_terms": ["password", "ssn", "credit card"]
  }
}
```

---

## Environment Configuration

### Backend `.env` (Required)

> **Complete reference: [SETUP.md](./SETUP.md)**

```env
# ─── DATABASE (Supabase PostgreSQL) ──────────────────────────────────
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres

# ─── REDIS (Upstash/Redis Cloud) ────────────────────────────────────
REDIS_URL=redis://default:PASSWORD@HOST:6379

# ─── QDRANT VECTOR DATABASE ────────────────────────────────────────
QDRANT_URL=https://CLUSTER.region.gcp.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key

# ─── AUTHENTICATION ─────────────────────────────────────────────────
JWT_SECRET=your-32-char-min-secret (generate: openssl rand -base64 32)

# ─── LLM PROVIDERS ─────────────────────────────────────────────────
OPENAI_API_KEY=sk-...           # Required for embeddings + chat
ANTHROPIC_API_KEY=sk-ant-...    # Optional: Claude fallback
# AZURE_OPENAI_*                # Optional: Azure OpenAI

# ─── FEATURE FLAGS ─────────────────────────────────────────────────
QDRANT_ENABLED=true
LITELLM_ENABLED=true
CELERY_ENABLED=true
```

### Frontend `.env`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### Widget `.env`

```env
SCOUT_API_URL=http://localhost:8000
SCOUT_WS_URL=ws://localhost:8000/ws
```

### Generate Secrets

```bash
# JWT Secret (32+ chars)
openssl rand -base64 32

# Or Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register org + user |
| POST | `/api/v1/auth/login` | Get access + refresh token |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Revoke refresh token |
| GET | `/api/v1/auth/me` | Get current user |

### Chatbots

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/chatbots` | List chatbots |
| POST | `/api/v1/chatbots` | Create chatbot |
| GET | `/api/v1/chatbots/{id}` | Get chatbot |
| PATCH | `/api/v1/chatbots/{id}` | Update chatbot |
| DELETE | `/api/v1/chatbots/{id}` | Delete chatbot |

### Knowledge Sources

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/knowledge-sources` | List sources |
| POST | `/api/v1/knowledge-sources` | Create source |
| GET | `/api/v1/knowledge-sources/{id}` | Get source |
| DELETE | `/api/v1/knowledge-sources/{id}` | Delete source |

### Widget API (Public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/widget/sessions` | Create session (returns token) |
| POST | `/api/v1/widget/messages` | Send message (requires token) |

### Developer API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/developer/api-keys` | List API keys |
| POST | `/api/v1/developer/api-keys` | Create API key |
| DELETE | `/api/v1/developer/api-keys/{id}` | Revoke API key |
| GET | `/api/v1/developer/widget-snippet` | Get embed code |
| **POST** | `/api/v1/developer/api-test` | **Test any endpoint** |
| **GET** | `/api/v1/developer/connectivity-test` | **Test external services** |
| **GET** | `/api/v1/developer/endpoints` | **List testable endpoints** |
| **POST** | `/api/v1/developer/test-chatbot/{id}` | **Full chatbot test** |

### Admin API (Admin Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/organizations` | List organizations |
| PATCH | `/api/v1/admin/organizations/{id}` | Suspend/activate |
| GET | `/api/v1/admin/audit-logs` | View audit trail |
| GET | `/api/v1/admin/health` | System health |
| GET | `/api/v1/admin/stats` | Platform statistics |

### Using API Keys

```bash
# Header-based auth
curl -H "X-API-Key: sco_xxxxxxxxxx" http://localhost:8000/api/v1/chatbots
```

---

## Storage Management

### Current Disk Usage

| Component | Size | Notes |
|-----------|------|-------|
| **Total** | ~300MB | After cleanup |
| Frontend | 270MB | node_modules + .next |
| Widget | 40MB | node_modules + dist |
| Backend | ~0MB | Cleaned .venv, cache |

### Cleanup Commands

```bash
# Backend
cd backend
rm -rf .venv .pytest_cache *.db __pycache__ .mypy_cache
uv pip cache purge

# Frontend
cd frontend
rm -rf node_modules .next
npm cache clean --force

# Widget
cd widget
rm -rf node_modules dist
npm cache clean --force

# Docker
docker system prune -a -f  # Remove unused images/containers
```

### Docker Storage

```bash
# Check Docker disk usage
docker system df

# Clean up
docker system prune -a --volumes -f
```

### Supabase/Qdrant Cloud

- **Supabase**: 500MB free tier (PostgreSQL)
- **Qdrant Cloud**: 1GB free tier (Vector DB)
- **Upstash Redis**: 100MB free tier

---

## Troubleshooting

### Common Issues

#### 1. Frontend: "Cannot find module './xxx.js'"

```bash
cd frontend
rm -rf .next
npm run dev
```

#### 2. Frontend: "Missing required error components" / Hydration Errors

**Cause:** Accessing `localStorage` during SSR.

**Fix:** Add mounted guard to pages:
```tsx
const [mounted, setMounted] = useState(false);
useEffect(() => { setMounted(true); }, []);
if (!mounted) return <Component {...pageProps} />;
```

#### 3. Backend: ModuleNotFoundError: No module named 'app'

**Cause:** Running from wrong directory.

```bash
# Correct
cd D:\PROJECTS\Scout.io\backend
uvicorn app.main:app --reload
```

#### 4. Backend: SQLite JSONB Error

**Cause:** Alembic migrations use PostgreSQL-specific `JSONB`.

**Fix:** Use Docker with PostgreSQL, or use test infrastructure (SQLite with `Base.metadata.create_all()`).

#### 5. Widget: TypeScript Build Errors

```bash
# Fixed errors:
# - adjustColor hoisting
# - React.KeyboardEvent vs native KeyboardEvent
# - <style jsx global> not supported
# - CSSProperties type annotations
# - useEffect cleanup return type
```

#### 6. Network: Cannot connect to localhost:8000/3000

**Cause:** Shell environment network restrictions.

**Fix:** Run in your local terminal, not in restricted shell.

#### 7. Port Conflicts

```bash
# Check ports
netstat -an | findstr "8000 3000 5432 6379 6333"

# Kill process on port
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess
```

#### 8. Docker Issues

```bash
# Restart Docker Desktop
# Then rebuild
docker compose -f docker/docker-compose.yml --profile full up --build -d
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health
# {"status": "ok", "service": "scout-api", "version": "0.4.0"}

# Backend readiness (checks DB, Redis, Qdrant)
curl http://localhost:8000/health/ready

# Frontend
curl http://localhost:3000
```

---

## Quick Reference Links

| Document | Purpose |
|----------|---------|
| [SETUP.md](./SETUP.md) | Server-side detailed setup |
| [ClientREADME.md](./ClientREADME.md) | Client/widget integration |
| [README.md](./README.md) | Project overview |
| [Progress.md](./Progress.md) | Implementation progress |
| API Docs | http://localhost:8000/docs |
| API Testing | http://localhost:3001/developer/api-test |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.4.0 | 2026-08-08 | Full Phase IV complete + API Testing |
| 0.3.0 | 2026-07-15 | Phase III: AI/RAG Pipeline |
| 0.2.0 | 2026-06-01 | Phase II: Core Platform |
| 0.1.0 | 2026-05-01 | Phase I: Foundation |

---

## Support

- **Documentation**: `/docs` folder
- **API Reference**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Email**: support@scout.io