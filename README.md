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
| AI Abstraction | LiteLLM (planned) |
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

## License

MIT
