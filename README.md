# Scout.io

**AI Knowledge Infrastructure Platform**

Scout.io is a multi-tenant AI platform that enables organizations to ingest, index, and query their knowledge bases using LLMs with RAG, policy-based access control, session management, and embeddable chat widgets.

## Tech Stack

| Component | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Frontend Dashboard | Next.js (TypeScript) + Tailwind CSS |
| Embeddable Widget | React (TypeScript) + Rollup |
| Database | PostgreSQL |
| Vector Database | Qdrant |
| Cache & Session | Redis |
| Background Tasks | Celery + Redis |
| AI Abstraction | LiteLLM |
| Payments | Razorpay Subscriptions (test-mode; feature-flagged) |
| Containerization | Docker + Docker Compose |

## Project Structure

```
scout.io/
├── backend/          # FastAPI Python backend
├── frontend/         # Next.js dashboard
├── widget/           # Embeddable chat widget
├── docker/           # Docker Compose & container config
├── scripts/          # Utility scripts
└── docs/             # Documentation
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (for containerized setup)
- [uv](https://github.com/astral-sh/uv) (Python package manager)

### Environment Setup

1. Clone the repository and copy environment templates:

```bash
scripts/setup_env.sh
```

This copies `.env.example` to `.env` for each component (root, backend, frontend, widget).

2. Configure the required variables in each `.env` file (see comments for guidance).

### Running with Docker (Recommended)

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build
```

### Running Locally

**Backend:**

```bash
cd backend
uv pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

**Widget:**

```bash
cd widget
npm install
npm run build
```

### Running Tests

```bash
cd backend && pytest
cd frontend && npm test
cd widget && npm test
```

## Features

- Multi-tenant orgs with JWT auth and role-based access control
- Chatbot management: create/rename/delete, model tiers, policies, widget snippets
- Knowledge sources: file upload (PDF/Markdown/DOCX/TXT), website, SQL/API/Git connectors
- Tenant dashboard: overview, settings, analytics (recharts), billing
- Analytics: org-scoped time-series, per-chatbot token usage, per-source usage
- Plans & billing via Razorpay Subscriptions (Starter/Growth/Scale), plan-limit enforcement
- Embeddable chat widgets (Python & JavaScript SDKs)
- PostgreSQL Row-Level Security for org isolation
- Secrets via HashiCorp Vault with env fallback in development

## Billing & Payments

Billing uses Razorpay Subscriptions and is controlled by a **feature flag**:

| Env var | Default | Meaning |
|---------|---------|---------|
| `BILLING_ENABLED` | `false` | `false` for testing/dev (no limit enforcement, checkout/webhook return 503, billing page shows "disabled"). Set `true` in production. |

Plan tiers (Free / Starter / Growth / Scale) and limits are documented in
[`docs/Plans and Billing.md`](docs/Plans%20and%20Billing.md). Razorpay keys are pulled
through the Vault wrapper (`backend/app/core/secrets.py`); only test-mode keys should be
configured until the account is KYC-activated for live mode.

## License

Scout.io is free and open-source software licensed under the
[GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html).

Copyright © 2026 Contributors of Scout.io

See the [LICENSE](LICENSE) file for the complete license text.
