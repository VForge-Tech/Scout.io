# Environment Setup

This guide covers wiring up the `.env` files for Scout.io, including the
HashiCorp Vault secret convention and the feature flags that control how the
stack runs. It applies to both local development and containerized deployment.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 20+ | Frontend / widget build |
| Docker & Docker Compose | Latest | Infrastructure |
| [uv](https://github.com/astral-sh/uv) | Latest | Python package manager |

## Creating `.env` files

Copy each `.env.example` template to a real `.env`:

```bash
scripts/setup_env.sh
```

This creates (only if missing) four files:

- `.env` (root — global, mostly documentation + Vault hints)
- `backend/.env` — the file that actually configures the backend
- `frontend/.env` — `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`
- `widget/.env` — `SCOUT_API_URL` / `SCOUT_WS_URL`

Edit `backend/.env` and add at least one LLM API key:

```env
OPENAI_API_KEY=sk-your-key-here
# or
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Backend environment variables

The complete reference is `backend/.env.example`. Key groups:

### Vault (secret management)

In production, secrets are stored in HashiCorp Vault and fetched at startup.
`.env` files only carry non-secret configuration and local dev defaults.

Path convention: `secret/scout-io/<environment>/<key>`

Required secrets per environment:

- `database_url`, `redis_url`, `qdrant_url`, `qdrant_api_key` (optional)
- `jwt_secret` (min 32 chars; generate with `openssl rand -base64 32`)
- `celery_broker_url`, `celery_result_backend`

Optional secrets:

- `openai_api_key`, `anthropic_api_key`, `together_api_key`, `gemini_api_key`,
  `azure_openai_api_key`, `webhook_secret`
- `razorpay_key_id`, `razorpay_key_secret`, `razorpay_webhook_secret`
  (test-mode keys only)

In **development**, set `VAULT_ADDR` + `VAULT_TOKEN` to use the local dev Vault
(`docker compose -f docker/docker-compose.yml up -d vault`), or simply set the
environment variables directly — Vault is optional in development. See
`docs/operations/security-and-compliance.md` for the production Vault setup.

### LLM providers & model tiers

```env
FAST_LLM_MODEL=gpt-3.5-turbo
BALANCED_LLM_MODEL=gpt-4o-mini
ACCURATE_LLM_MODEL=gpt-4o
FALLBACK_MODELS=["claude-3-haiku-20240307", "gemini/gemini-1.5-flash"]
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

### Retrieval & context

```env
MAX_CONTEXT_TOKENS=4096
MAX_RESPONSE_TOKENS=1024
TOP_K_RETRIEVAL=5
```

### Redis cache TTLs

```env
REDIS_SESSION_TTL_SECONDS=3600
REDIS_KNOWLEDGE_CACHE_TTL=300
REDIS_OPTIMIZATION_CACHE_TTL=600
```

### CORS & rate limiting

```env
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001", "http://localhost:8000"]
RATE_LIMIT_PER_IP=100/minute
RATE_LIMIT_PER_ORG=1000/minute
```

### Feature flags

```env
QDRANT_ENABLED=true      # vector search (falls back to pgvector/keyword)
LITELLM_ENABLED=true     # AI provider abstraction
CELERY_ENABLED=true      # background ingestion/aggregation
PGVECTOR_ENABLED=false   # Postgres vector fallback
OLLAMA_ENABLED=false     # local LLMs
MOCK_LLM=false           # deterministic mock replies (load testing)
RERANKER_ENABLED=false   # cross-encoder reranking service
BILLING_ENABLED=false    # Razorpay; set true in production
```

### Billing

`BILLING_ENABLED` defaults to `false`. When off, plan limits are not enforced
and the checkout/webhook endpoints return 503. Set `true` in production with
test-mode Razorpay keys until the account is KYC-activated. See
`docs/integrations/billing-razorpay.md`.

### Ollama (optional local LLMs)

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2
```

## Frontend `.env`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Widget `.env`

```env
SCOUT_API_URL=http://localhost:8000
SCOUT_WS_URL=ws://localhost:8000/ws
```

## Generating secrets

```bash
# JWT secret (32+ chars)
openssl rand -base64 32

# Or Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Next steps

- Run the stack locally: `docs/getting-started/local-development.md`
- Deploy with Docker Compose: `docs/getting-started/demo-deployment.md`
- Provision production Vault: `docs/operations/security-and-compliance.md`