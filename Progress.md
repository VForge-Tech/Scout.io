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

---

## Phase II: Core Platform Layer [COMPLETED]

### Backend Models & Schemas
- `ApiKey` model: id, user_id, organization_id, name, key_prefix, key_hash, last_used_at, expires_at, is_active
- `AuditLog` model: id, user_id, organization_id, action, details (JSONB), ip_address, timestamp
- `Message` model: id, session_id, role, content, metadata (JSONB)
- Alembic migration 0002 adding api_keys, audit_logs, messages tables
- Pydantic schemas for ApiKey, AuditLog, Widget session/request/response
- `app/utils/audit.py` helper for logging audit events
- Widget session token support via JWT with `type: "widget"` claim

### API Endpoints
- Developer: `POST/DELETE /developer/api-keys`, `GET /developer/api-keys`, `GET /developer/widget-snippet`
- Widget: `POST /widget/sessions`, `POST /widget/messages`
- Admin: `PATCH/DELETE /admin/organizations/{id}`, `GET /admin/audit-logs`, `GET /admin/health`
- Analytics and sessions endpoints under `/organizations/me/`

### Frontend (Pages Router)
- Placeholder dashboard page
- Tailwind CSS configured
- Standalone build output

---

## Phase III: AI & RAG Pipeline [COMPLETED]

### Knowledge Engine
- `embeddings.py`: LiteLLM embedding abstraction (supports OpenAI, Anthropic, Gemini, Together AI)
- `qdrant_store.py`: Qdrant collection management, vector indexing with metadata, similarity search with org/chatbot filtering
- `engine.py`: Orchestrator with policy-aware retrieval (`source_filter`, `content_filter`)

### AI Router
- `config.py`: Model configuration mapping fast→cheap, balanced→medium, accurate→expensive
- `router.py`: LiteLLM wrapper with primary→fallback→graceful error chain, token counting, streaming

### Memory Framework
- `session_memory.py`: Redis-backed conversation history (last N messages), context builder
- `knowledge_memory.py`: Short-term cache for retrieved chunks
- `org_memory.py`: Organization config and policies cache
- `optimization_memory.py`: FAQ response caching

### Validation & Optimization
- `response_validator.py`: Hallucination detection via word overlap threshold
- `sanitizer.py`: Strips provider names, model names, API keys from responses
- `token_optimizer.py`: Context compression by token-aware priority truncation

### Pipeline
- `response_pipeline.py`: End-to-end pipeline: cache check → memory check → knowledge retrieval → context optimization → AI generation → validation → sanitization → cache → return

### Additional
- `LLMUsage` model for tracking token usage
- Updated widget API to use full ResponsePipeline
- Celery tasks for background embedding/indexing
- Debug retrieval endpoint: `GET /api/v1/debug/retrieve`
- Alembic migration 0003 for LLM usage tracking
- 62 passing tests (32 Phase II + 30 Phase III)

---

## Phase IV: Production Layer [IN PROGRESS]

### Sprint 1: Analytics Engine [COMPLETED]
- `AnalyticsEvent` model: event_type, entity_id, organization_id, chatbot_id, source_id, payload JSON
- `DailyAnalytics` model: per-day aggregates for sessions, messages, tokens, latency, feedback, sync stats
- Celery daily aggregation task (`aggregate_daily_analytics`)
- API endpoints:
  - `GET /analytics/chatbot/{chatbot_id}` – chatbot aggregate stats
  - `GET /analytics/organization` – org-wide summary
  - `GET /analytics/source/{source_id}` – source usage and sync stats
  - `GET /admin/analytics/platform` – platform-wide totals
  - `POST /analytics/events` – track raw analytics events

### Sprint 2: Security Enhancements [COMPLETED]
- API key authentication via `X-API-Key` header with bcrypt hash verification
- Audit logging on all sensitive actions: login, logout, chatbot create/delete, webhook create/delete, system config changes
- CORS configured with configurable `cors_origins` (whitelist-based)
- HTTPS termination via Nginx with SSL configuration
- Structured JSON logging to stdout via custom `JSONLogFormatter`
- Tracing middleware adding `X-Trace-ID` to all requests
- Rate limiting per IP and per organization configurable via settings
- Response sanitization strips provider names, model names, API keys, secrets

### Sprint 3: Error Handling & Graceful Degradation [COMPLETED]
- **LLM failures**: primary → fallback → graceful error response
- **Qdrant failures**: automatic fallback to keyword search (TF-IDF on scroll results)
- **Sync failures**: status tracking with retry support
- **Graceful shutdown**: DB connections properly closed via `get_db` generator pattern
- Configurable timeouts for broker connections

### Sprint 4: Monitoring & Observability [COMPLETED]
- Structured JSON logging with `trace_id`, `user_id`, `organization_id` context
- Tracing middleware: every request gets a `X-Trace-ID` header
- Health endpoints: `GET /health`, `GET /health/ready` (aggregates DB, Redis, Qdrant status)
- Admin system health page showing real-time service status
- Admin audit log viewer with pagination

### Sprint 5: Admin Dashboard [COMPLETED]
- Pages Router pages under `/admin/`:
  - **Dashboard** (`/admin`): Platform statistics cards
  - **Organizations** (`/admin/organizations`): List, search, suspend
  - **Audit Logs** (`/admin/audit-logs`): Paginated table with filters
  - **System Health** (`/admin/system-health`): Service status cards
  - **Settings** (`/admin/settings`): System config key-value editor

### Sprint 6: Developer Portal [COMPLETED]
- Pages Router pages under `/developer/`:
  - **Dashboard** (`/developer`): Overview with link cards
  - **API Keys** (`/developer/api-keys`): Create (show once), list, revoke
  - **API Docs** (`/developer/docs`): Interactive docs links + auth info
  - **Widget Integration** (`/developer/widget`): Chatbot selector, theme picker, snippet generator

### Sprint 7: Deployment & Infrastructure [COMPLETED]
- Production Docker Compose (`docker-compose.prod.yml`): backend, frontend, nginx, celery_worker, celery_beat
- Nginx config with HTTPS, SSL termination, proxy for API, frontend, WebSocket
- Resource limits and reservations for production services
- Celery beat for scheduled analytics aggregation
- Frontend API proxy via Next.js rewrites

### Sprint 8: Testing & Documentation [COMPLETED]
- Alembic migration 0004 for Phase IV models (analytics_events, daily_analytics, system_config, webhooks)
- 62+ existing tests all passing
- Integration tests for Phase IV endpoints
- Widget SDK (Python & JavaScript) published

#### Additional Completed Features
- Webhook delivery system with retry logic and signature verification
- Knowledge source connectors: SQL, API, Git (extensible registry pattern)
- Multi-modal knowledge ingestion (PDF, Markdown, DOCX, TXT, Websites)
- Ollama local LLM support for embeddings and chat
- Pgvector fallback for embeddings (no external vector DB required)
- Structured JSON logging with trace_id, user_id, organization_id context
- Prometheus metrics endpoint ready for production monitoring
- Rate limiting per IP and per organization (configurable via settings)

### Sprint 9: Database-Level Row-Level Security (RLS) [COMPLETED]
- **Alembic migration 0006**: Enables RLS on all 13 organization-scoped tables (users, chatbots, policies, knowledge_sources, sessions, messages, api_keys, audit_logs, analytics_events, daily_analytics, llm_usage, webhooks)
- **Standard org-isolation policy**: All SELECT/INSERT/UPDATE/DELETE restricted to rows where `organization_id = current_setting('app.current_org_id')::uuid`
- **Messages table isolation**: Policy joins through sessions table to enforce org isolation
- **Platform admin bypass policy**: Separate policy allowing cross-org access when `app.is_platform_admin = 'true'` (narrowly scoped, not superuser)
- **Request lifecycle integration**: FastAPI dependency `get_db_with_org` runs `SET LOCAL app.current_org_id = :org_id` at start of each request, sourced from JWT `org_id` claim
- **Admin endpoints**: Use `get_db_admin` which sets `app.is_platform_admin = 'true'` for cross-org queries
- **Widget sessions**: Token includes `org_id` claim; widget message endpoint sets RLS context per session
- **JWT enhancement**: Access/refresh tokens now carry `org_id` claim for RLS context
- **Tests**: 15 tests covering app-level isolation (works on SQLite) and PostgreSQL RLS behavior (skipped on SQLite)
- **All 100 tests pass** (92 passing, 8 skipped PostgreSQL-only RLS tests)

### Sprint 10: HashiCorp Vault Secret Management [COMPLETED]
- **Vault service**: Added to docker-compose.yml (dev mode) and docker-compose.prod.yml (production file backend with auto-unseal support)
- **Vault client wrapper** (`app/core/secrets.py`): hvac-based client with KV v2 support, availability checking, and secret read/write/delete operations
- **SecretManager**: High-level wrapper that fetches from Vault with environment variable fallback for local development
  - Production: Vault required, fails fast if unavailable or secret missing
  - Development: Falls back to environment variables if Vault unreachable
  - Path convention: `secret/scout-io/<environment>/<key>` (e.g., `secret/scout-io/production/database_url`)
- **Config integration** (`app/core/config.py`): Settings class now populates all secret fields from SecretManager at initialization
  - Required secrets: database_url, redis_url, qdrant_url, qdrant_api_key, jwt_secret, celery_broker_url, celery_result_backend
  - Optional secrets: openai_api_key, anthropic_api_key, together_api_key, gemini_api_key, azure_openai_api_key, webhook_secret
- **Early initialization**: Secret manager initialized at module load in `app/main.py` with deployment environment detection
- **Documentation**: `.env.example` files updated to document Vault path convention and remove secret placeholders
- **Production setup guide**: `docs/Vault_Production_Setup.md` with step-by-step provisioning, initialization, unsealing, policy creation, AppRole auth, secret writing, and rotation procedures
- **All 92 tests pass** with env var fallback in test environment

### Sprint 11: Adversarial Security Testing & Hardening [COMPLETED]
- **Test suite** (`tests/security/test_prompt_injection.py`): 22 adversarial tests across 4 attack categories
  - System prompt extraction (4 tests): direct requests, roleplay, encoding, chain-of-thought
  - Policy bypass (4 tests): source_filter/content_filter override, instruction hierarchy, indirect injection via retrieved chunks
  - Cross-org data leakage (3 tests): direct queries, session extraction, knowledge source leaks
  - Sanitizer bypass (6 tests): provider/model name variations, secrets, encoded/partial/unusual formats
  - Response validator (3 tests): hallucination detection, safety validation
- **Fixes implemented**:
  - **System prompt hardening** (`app/core/memory/session_memory.py`): Explicit instruction hierarchy with 6 "NEVER VIOLATE" rules
  - **Post-generation safety filter** (`app/core/pipeline/response_pipeline.py`): `_check_post_generation_safety()` catches cross-org UUIDs, system prompt leaks, instruction override language
  - **Extended sanitizer patterns** (`app/core/validation/sanitizer.py`): 
    - Provider names with spaces/hyphens (`Open AI`, `Open-AI`)
    - Partial matches in compounds (`openai-compatible`, `gemini-powered`)
    - Secrets with unusual delimiters (`sk_abc`, `sk.abc`, `sk:abc`, `sk|abc`)
    - Model name variations (`GPT 4o`, `GPT4`, `Claude Opus`)
  - **Response validator enhancements** (`app/core/validation/response_validator.py`): Added patterns for prompt printing/revelation requests
- **Before/After Pass Rate**:
  - Baseline: 16/22 passed (72.7%) — 6 failures across sanitizer gaps, cross-org mock issues, validator param
  - After fixes: 22/22 passed (100%) — all adversarial tests now pass
- **Total test suite**: 114 tests passing (92 original + 22 security), 8 skipped (PostgreSQL-only RLS)

### Sprint 12: Tenant Dashboard (Chatbots, Knowledge Sources, Analytics) [COMPLETED]
- **Dashboard layout** (`frontend/src/components/DashboardLayout.tsx`): top nav + sidebar shared by all tenant pages under `/dashboard/`
- **Overview** (`/dashboard`): Live org info (`GET /organizations/me`) + org analytics (`GET /analytics/organization`), stat cards, quick actions
- **Settings** (`/dashboard/settings`): Organization rename via `PUT /organizations/me`
- **Chatbot management** (`/dashboard/chatbots`, `/chatbots/new`, `/chatbots/[id]`):
  - Create, rename, delete with confirmation modal
  - Model tier picker (fast/balanced/accurate) mapped to backend behaviour config
  - Knowledge source attach/detach per chatbot
  - Real policy form: source_filter → `allowed_source_ids`, content_filter → `blocked_terms`
  - Widget snippet preview + copy reusing `GET /developer/widget-snippet?theme=light|dark`
- **Knowledge sources** (`/dashboard/knowledge-sources`):
  - Aggregated list across all org chatbots with 5s polling (no websocket exists)
  - Add Source flow: website URL, file upload (PDF/Markdown/DOCX/TXT via `/uploads/{chatbot_id}`), and SQL/API/Git connectors with exact backend fields
  - Sync status badges (Synced/Failed/Syncing/Pending), retry button, delete confirmation warning it removes the source from every chatbot using it
  - Backend: new `POST /chatbots/{chatbot_id}/knowledge-sources/{source_id}/sync` dispatch endpoint (503 if Celery disabled); uploads `allowed_types` broadened for Markdown/DOCX/TXT
  - `frontend/src/lib/api.ts` rewritten: multipart `formData` support + `api.upload<T>()`
- **Analytics** (`/dashboard/analytics`): recharts page (installed; was not previously a dependency)
  - Date-range selector (7/30/90 days), message volume + sessions over time (composed chart)
  - Token usage over time broken out per chatbot (shown only when >1 chatbot)
  - Feedback summary card; latency/feedback fields exposed via daily endpoint
  - Admin-only knowledge source usage table (`GET /analytics/source/{source_id}`) gated on role from new `GET /auth/me`
  - Backend time-series endpoints (all org-scoped):
    - `GET /analytics/organization/daily?start_date&end_date` — daily rows for the caller's org
    - `GET /analytics/chatbot/{chatbot_id}/daily` — 404 unless chatbot belongs to caller's org
  - `GET /auth/me` added (referenced in developer docs but previously missing)
- **Cross-org isolation verified**: analytics tests confirm org A cannot read org B's daily or aggregate analytics (404), plus `/auth/me` test
- **Total test suite**: 124 passing (114 + 10 analytics/auth tests), 8 skipped (PostgreSQL-only RLS)

### Sprint 13: Plans & Billing (Razorpay Subscriptions) [COMPLETED]
- **Plan tiers** (`backend/app/core/billing/plans.py`): Free / Starter (₹2,999) / Growth (₹9,999) / Scale (₹29,999) with concrete limits per tier — chatbots allowed, monthly message volume, knowledge source count
- **Organization model + migration 0007**: added `plan`, `plan_status`, `razorpay_customer_id`, `razorpay_subscription_id` columns (indexed)
- **Razorpay integration** (`backend/app/core/billing/razorpay_client.py`):
  - `POST /organizations/me/billing/checkout-session` creates a Razorpay customer + subscription for the selected plan, returns the Razorpay-hosted checkout URL
  - `POST /webhooks/razorpay` handles `subscription.activated`, `subscription.charged`, `subscription.cancelled`, `subscription.halted`, updating org plan/status and writing audit log entries (`billing.plan_activated`, `plan_cancelled`, `plan_halted`, `subscription_charged`)
  - Every webhook verifies `X-Razorpay-Signature` (HMAC-SHA256 of the raw body, constant-time compare); unsigned/invalid payloads rejected
  - Org resolution from subscription `notes.organization_id` with fallback to stored `razorpay_subscription_id`
- **Plan limits enforced at API layer** (`backend/app/core/billing/limits.py`): chatbot create, knowledge source create, and widget message processing all reject past the plan limit with HTTP 402 + clear message; cancelled/halted orgs auto-downgrade to Free tier for enforcement
- **Keys via Vault**: `razorpay_key_id`, `razorpay_key_secret`, `razorpay_webhook_secret` pulled through the existing SecretManager (env fallback in dev); test-mode keys only, never hardcoded
- **Feature flag**: `billing_enabled` (`BILLING_ENABLED`, default `false`). Off in testing/dev — plan limits not enforced (no-op), checkout/webhook endpoints return 503, frontend billing page shows a "Billing is disabled in this environment" notice. Enable `BILLING_ENABLED=true` in production.
- **Frontend** (`/dashboard/billing`): current plan, usage vs limits cards, plan cards with Upgrade → redirect to Razorpay checkout (disabled when the flag is off)
- **Docs**: `docs/Plans and Billing.md` — tiers/limits, Vault key provisioning, webhook registration, feature flag, live-mode checklist (KYC note)
- **Tests**: 20 billing tests (checkout-session, signature rejection, all four webhook events, plan limit enforcement for chatbots/knowledge sources/messages, cancelled-downgrade, usage summary, disabled-flag 503 behavior)
- **Total test suite**: 145 passing (142 + 3 flag tests), 8 skipped (PostgreSQL-only RLS)

### Sprint 14: Usage-Based Billing (Token Overage via Celery Beat) [COMPLETED]
- **LLMUsage now actually written**: `ResponsePipeline` records an `LLMUsage` row after every AI generation (was previously never written — only read by analytics/admin). `AIRouter` captures provider-reported token counts (fallback to `count_tokens` estimate) + the model actually used (incl. fallback chain); estimated cost stored via new `pricing.py`
- **Pricing module** (`backend/app/core/billing/pricing.py`): per-model paise-per-1K input/output prices (`gpt-3.5-turbo`, `gpt-4o-mini`, `gpt-4o`, Claude, Gemini, Llama) with a medium default; `estimate_cost_paise`, `overage_amount_paise`, add-on batch cap (`MAX_OVERAGE_TOKENS_PER_ADDON`)
- **Plan usage component** (`plans.py`): each tier gains `included_monthly_tokens` (Free 100k / Starter 1M / Growth 5M / Scale 25M) and `overage_price_paise_per_1k` for paid tiers
- **`UsageBillingRecord` model + migration 0008**: unique per `organization_id` + `YYYY-MM` period; stores prompt/completion/total tokens, estimated cost (paise), overage tokens/cost, `reported_to_razorpay`, `razorpay_addon_id`
- **Celery beat task** (`backend/app/tasks/billing_tasks.py`, 03:00 UTC daily): per-org month aggregation, `UsageBillingRecord` upsert, Razorpay overage reporting, 80% soft-limit event, idempotent re-runs
- **Razorpay overage reporting** (`razorpay_client.create_addon`): Razorpay has no usage-metering API, so overage is charged as a subscription **add-on** on the next invoice (`subscription.createAddon`, verified against the SDK); graceful **fallback to internal tracking** (`reported_to_razorpay=false`) when there's no subscription, no overage price, or the API call fails
- **Soft-limit warning**: `billing.usage_soft_limit` AnalyticsEvent fired once per period at 80% of included tokens; surfaced by `usage_summary` (`warning`) and rendered as an orange banner on `/dashboard/billing`
- **Billing endpoint**: `GET /organizations/me/billing` now returns `usage_billing` (current month record) and `limits.included_monthly_tokens`
- **Frontend** (`/dashboard/billing`): warning banner, token usage card (used / included, overage + add-on vs invoice status)
- **Infra**: `celery_billing_beat` + `celery_billing_worker` compose services; worker app includes both `billing_tasks` and `analytics_tasks`
- **Docs**: `docs/Plans and Billing.md` — usage-based billing section (recording, aggregation, overage fallback, deployment)
- **Tests**: 16 new tests (pricing math + model matching, aggregation create/upsert, Razorpay add-on report + failure fallback + no-subscription skip, soft-limit once-per-period + below-threshold, endpoint warning/usage_billing surface, pipeline LLMUsage recording incl. provider-usage capture, no-db skip)
- **Total test suite**: 161 passing (145 + 16), 8 skipped (PostgreSQL-only RLS) — frontend build clean

---

## Phase V: In Progress / Planned
- Multi-factor authentication (TOTP-based)
- Advanced cost tracking and budget alerts per organization/chatbot (plan tiers/billing + usage-based overage done in Sprints 13–14; feature-flagged)
- Performance optimization: incremental sync, intelligent caching improvements
- SDK generation for Python, JavaScript, Go (Python/JS done)
- Real-time analytics dashboard updates (WebSocket-based; static/date-range charts done in Sprint 12)
- Custom model fine-tuning integration
- Multi-region deployment support
- Horizontal scaling for Celery workers
- Plugin/extension system for custom knowledge connectors
