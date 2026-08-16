# Scout.io

**AI Knowledge Infrastructure Platform**

Scout.io is a multi-tenant AI platform that enables organizations to ingest,
index, and query their knowledge bases using LLMs with RAG, policy-based access
control, session management, and embeddable chat widgets.

## Tech Stack

| Component | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Frontend Dashboard | Next.js (TypeScript) + Tailwind CSS |
| Embeddable Widget | React (TypeScript) + Rollup |
| Database | PostgreSQL (Row-Level Security) |
| Vector Database | Qdrant (+ pgvector, optional reranker) |
| Cache & Session | Redis |
| Background Tasks | Celery + Redis |
| AI Abstraction | LiteLLM |
| Payments | Razorpay Subscriptions (test-mode; feature-flagged) |
| Secrets | HashiCorp Vault (env fallback in dev) |
| Containerization | Docker + Docker Compose |

## Project Structure

```
scout.io/
├── backend/          # FastAPI Python backend
├── frontend/         # Next.js dashboard
├── widget/           # Embeddable chat widget
├── sdk/              # JavaScript & Python SDKs
├── docker/           # Docker Compose & container config
├── load-tests/       # Locust load-testing suite
├── scripts/          # Utility scripts
├── docs/             # Documentation (start at docs/README.md)
└── LICENSE
```

## Quick Start

Prerequisites: Python 3.12+, Node.js 20+, Docker & Docker Compose, `uv`.

```bash
# 1. Copy .env templates for each component
scripts/setup_env.sh

# 2. Configure credentials in each .env (see docs/getting-started/environment-setup.md)

# 3. Full stack with Docker (infra + backend + frontend + widget services)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build

# 4. Or run the backend locally
cd backend
uv pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

**Access points:** Frontend dashboard `http://localhost:3000` · Backend API
`http://localhost:8000` · API docs `http://localhost:8000/docs` ·
API testing `http://localhost:3001/developer/api-test`

> Expected test baseline: **216 passed, 8 skipped** (`cd backend && pytest`).

## Features

- Multi-tenant orgs with JWT auth, TOTP two-factor auth, and RBAC
- Chatbot management: create/rename/delete, model tiers, policies, widget snippets
- Knowledge sources: file upload (PDF/Markdown/DOCX/TXT), website, SQL/API/Git connectors
- Tenant dashboard: overview, settings, analytics, billing
- Analytics: org-scoped time-series, per-chatbot token usage, per-source usage
- Plans & billing via Razorpay Subscriptions (Free/Starter/Growth/Scale), plan-limit enforcement
- Embeddable chat widgets (JavaScript & Python SDKs)
- PostgreSQL Row-Level Security for org isolation
- Secrets via HashiCorp Vault with env fallback in development
- Observability: Prometheus + Grafana + Loki + Alertmanager, tracing

## Documentation

See the **[docs/README.md](docs/README.md)** table of contents. Quick pointers:

- [Environment setup](docs/getting-started/environment-setup.md)
- [Local development](docs/getting-started/local-development.md)
- [Demo deployment](docs/getting-started/demo-deployment.md)
- [Client guide](docs/guides/client-guide.md)
- [Admin guide](docs/guides/admin-guide.md)
- [Developer portal & API](docs/guides/developer-portal-guide.md)
- [System architecture](docs/architecture/system-architecture.md)
- [Roadmap](docs/roadmap.md)

## License

Scout.io is free and open-source software licensed under the
[GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html).

Copyright © 2026 Contributors of Scout.io

See the [LICENSE](LICENSE) file for the complete license text.