# Scout.io Setup Guide

## Quick Demo (Tests Only — No Infrastructure Required)

Everything in Phase V can be verified via tests with **zero external services**:

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

All 85 tests should pass. This covers:
- **Connector Framework**: registry, validation, graceful failure
- **Event Bus**: pub/sub, sync/async, error isolation
- **Domain Services**: chatbot, knowledge, analytics event publishing
- **Multi-modal**: message_type defaults, attachments
- **Backward Compatibility**: existing knowledge source endpoints unchanged
- **Knowledge Sources with connector_type**: create with connector_type, defaults without
- **Feature Flags**: default values for `QDRANT_ENABLED`, `LITELLM_ENABLED`, `PGVECTOR_ENABLED`, `OLLAMA_ENABLED`

## Full Stack Demo

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- [uv](https://github.com/astral-sh/uv)

### 1. Environment

```bash
scripts/setup_env.sh
```

Edit `backend/.env` and add at least one LLM API key (e.g. `OPENAI_API_KEY`).

### 2. Start Infrastructure (PostgreSQL + Redis + Qdrant)

```bash
docker compose -f docker/docker-compose.yml up -d postgres redis qdrant
```

For minimal profile (no Qdrant):

```bash
docker compose -f docker/docker-compose.yml up -d postgres redis
```

For full stack with Ollama / pgvector:

```bash
docker compose -f docker/docker-compose.yml --profile full up -d
```

### 3. Run Backend

```bash
cd backend
uv pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs

### 4. Demo Phase V Features

#### Connectors
```bash
# Create an API connector knowledge source
curl -X POST http://localhost:8000/api/v1/chatbots/{bot_id}/knowledge-sources \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"source_type": "api", "uri": "https://api.example.com/data", "connector_type": "api"}'
```

#### SDK
```python
from scout_sdk import ScoutClient, ScoutConfig
client = ScoutClient(ScoutConfig(api_key="sk-..."))
resp = client.send_message(chatbot_id="...", content="Hello")
```

#### File Upload
```bash
curl -X POST http://localhost:8000/api/v1/uploads/{chatbot_id} \
  -H "Authorization: Bearer {token}" \
  -F "file=@example.png"
```

### 5. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard at http://localhost:3000

## Docker Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| (none) | postgres, redis, qdrant, backend | Full production |
| `--profile minimal` | postgres, redis, backend | No Qdrant |
| `--profile ollama` | + ollama | Local LLMs |
| `--profile pgvector` | + pgvector | PostgreSQL vectors |

Set `QDRANT_ENABLED=false`, `OLLAMA_ENABLED=true`, `PGVECTOR_ENABLED=true` in `backend/.env` accordingly.
