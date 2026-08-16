# Scout.io — Privacy / Terms / DPA Drafting Brief

**Status:** Technical fact base for drafting the Privacy Policy, Terms of Service, and Data
Processing Agreement.

**Prepared:** 2026-08-16

**How to use this document:** This is NOT final legal language. It is a fact base a lawyer can
work from directly. Every claim is sourced from the Scout.io codebase (verified) or from the
named provider's public policy (researched 2026-08-16; provider policies change frequently).
Items marked **[VERIFY]** are deployment-dependent or policy-dependent and MUST be confirmed
against production before anything is published. A consolidated verification checklist is in
Section 8.

---

## 1. What customer data Scout.io ingests, and why

### 1.1 Documents / knowledge sources (customer-uploaded content)

- **Upload endpoint:** `POST /uploads/{chatbot_id}`
  (`backend/app/api/endpoints/uploads.py:15-31`).
- **Accepted file types:** PNG, JPEG, GIF, PDF, plain text, Markdown, `.docx`, `.doc`.
  Files with other MIME types are rejected with HTTP 400.
- **Storage of originals:** raw bytes are written to
  `UPLOAD_DIR/<org_id>/<chatbot_id>/<file_id><ext>` (default `/tmp/scout_uploads`, env
  `UPLOAD_DIR`). Only metadata `{file_id, filename, content_type, size_bytes, url}` is kept
  in the database.
- **Why it is ingested:** the content is the customer's knowledge base. A `KnowledgeSource`
  record stores `source_type`, `uri`, `config`, `sync_status`. A Celery task
  (`backend/app/tasks/embedding_tasks.py`) chunks the content and passes the chunks to the
  embedding service, which sends chunk text to the configured embedding model via LiteLLM
  (`backend/app/core/knowledge/embeddings.py`).
- **Where the processed form lives:** chunk text + its embedding vector are stored in the
  vector store — the Qdrant collection `scout_knowledge` (payload includes `organization_id`,
  `chatbot_id`, text, chunk index) or, when enabled, the pgvector fallback table
  `knowledge_vectors` (`backend/app/core/knowledge/qdrant_store.py`,
  `backend/app/core/knowledge/pgvector_store.py`).
- **Default embedding model:** `text-embedding-3-small` (OpenAI), dimension 1536
  (`backend/.env.example:85-87`).
  **[VERIFY]** — confirm the production embedding model; if it is an OpenAI model, document
  chunk content is transmitted to OpenAI's embedding API, which the DPA must disclose.

### 1.2 Chat content

- **Widget flow:** `POST /widget/sessions` then `POST /widget/messages`
  (`backend/app/api/endpoints/widget_api.py`). Each user message is stored in the `messages`
  table (`role`, `content`, `attachments`, `metadata`), linked to a `sessions` row.
- **Chat content leaves Scout's infrastructure:** the response pipeline
  (`backend/app/core/pipeline/response_pipeline.py:177-193`) retrieves relevant document
  chunks, builds a prompt (system prompt + retrieved context + session history), and calls
  the LLM provider via LiteLLM. **Both the end user's question and the retrieved document
  content are sent to the configured LLM provider.** This is a core fact for the DPA.
- **Transient cache:** session history is cached in Redis under
  `session:{session_id}:history` (TTL 1 hour). Chat content is therefore transiently in
  Redis.
- **Widget identity fields:** the widget session accepts an optional `customer_id` and
  free-form `metadata` (`backend/app/schemas/widget.py`). Scout stores these verbatim and
  does not interpret them — they may contain end-user PII provided by the customer.

### 1.3 Account / personal data (controller-side)

- `users`: email, bcrypt `hashed_password` (never plaintext), full name, role.
- `organizations`: name, plan, plan status, Razorpay customer/subscription IDs.
- `audit_logs`: action, `details` (JSON), `ip_address`, timestamp — records admin/org actions.
- `llm_usage` / `analytics_events` / `daily_analytics`: token counts, model, latency, usage
  metrics. **No message content.**
- `api_keys`: developer-issued keys (`key_prefix`, `key_hash`).

---

## 2. Where the data is stored

| Store | What it holds | Deployment location / region |
|---|---|---|
| PostgreSQL | Account data, messages, sessions, knowledge sources, policies, audit logs, usage/billing | Compose service `postgres` (volume `postgres_data`). Repo defines no cloud/region; GUIDE.md example references **Supabase PostgreSQL**. **[VERIFY]** prod host/region |
| Qdrant | Document chunk vectors + text payloads | Compose service `qdrant` (volume `qdrant_data`). GUIDE.md example references **Qdrant Cloud on GCP** (`CLUSTER.region.gcp.cloud.qdrant.io`). **[VERIFY]** prod host/region |
| Redis | Session history, knowledge cache, optimization cache, org memory | Compose service `redis` (volume `redis_data`). TTLs: session 1h, knowledge cache 5 min, opt cache 10 min. GUIDE.md example references **Upstash / Redis Cloud**. **[VERIFY]** prod host/region |
| Uploads | Raw source files | Local FS `UPLOAD_DIR/<org_id>/...`. **[VERIFY]** whether prod uses a persistent volume or object store |
| Backups | Postgres dump + Qdrant snapshot | S3-compatible object store (any provider — see Section 4). **[VERIFY]** prod provider/bucket region |
| Secrets | HashiCorp Vault | Self-hosted compose service. **[VERIFY]** prod Vault host/region |

**No single fixed cloud/region is defined in the repository.** Region commitments and
transfer-safeguard clauses in the Privacy Policy/DPA must be filled in from the actual
production deployment. **[VERIFY]**

---

## 3. Third-party subprocessors

### 3.1 LLM providers (via LiteLLM)

Source: `backend/app/core/ai/config.py`, `backend/app/core/ai/router.py`,
`backend/.env.example:25-30, 85-127`.

- **Primary provider — OpenAI.** Defaults per behavior tier: `gpt-3.5-turbo` (fast),
  `gpt-4o-mini` (balanced), `gpt-4o` (accurate). **[VERIFY]** production values come from
  Vault and may differ from dev defaults.
- **Fallback chain** (`FALLBACK_MODELS`): `claude-3-haiku-20240307` (Anthropic),
  `gemini/gemini-1.5-flash` (Google Gemini via LiteLLM). Fallbacks fire automatically when
  the primary fails (`backend/app/core/ai/router.py:39-62`).
  **[VERIFY]** which fallbacks are provisioned in production and whether they actually fire.
- **Optional providers with Vault secret slots:** Anthropic, Together AI, Google Gemini,
  Azure OpenAI, OpenAI (`backend/.env.example:25-30`).
  **[VERIFY]** which of these are actually enabled in production.
- **Local option — Ollama** (`OLLAMA_ENABLED`, local embedding `nomic-embed-text`, chat
  `llama3.2`): data never leaves Scout's infrastructure. **[VERIFY]** enabled in prod or not.
- **Embeddings:** `text-embedding-3-small` (OpenAI) — document chunk content is transmitted
  to OpenAI's embedding API (see 1.1).

### 3.2 Payments — Razorpay (NOT Stripe) ⚠️

The draft brief referenced "Stripe", but the codebase uses **Razorpay**:
`backend/app/core/billing/razorpay_client.py`, `backend/app/api/endpoints/billing.py`,
migrations `0007_plan_billing` / `0008_usage_billing_records`. Razorpay handles
subscriptions, plan changes, cancellations, usage-overage addons, and webhooks. **No Stripe
code exists in the repository.**

**[VERIFY]** — if Stripe is used in production despite the codebase using Razorpay, that
discrepancy must be resolved before publishing.

### 3.3 Hosting / cloud provider

No hosting provider is pinned in the repository. Deployment is Docker Compose with container
images published to **GHCR** (`.github/workflows/build.yml`). GUIDE.md's example deployment
references **Supabase (Postgres)**, **Upstash (Redis)**, and **Qdrant Cloud (GCP)**.
**[VERIFY]** the actual production hosting provider and region(s) — required for DPA transfer
safeguards and subprocessor disclosure.

### 3.4 Other external services

- **Backup object storage:** any S3-compatible endpoint (`S3_ENDPOINT`, e.g.
  `https://s3.amazonaws.com` or self-hosted MinIO). Nightly upload of a Postgres dump and a
  Qdrant snapshot (`docker/backup/backup.sh`). **[VERIFY]** provider/bucket region in prod.
- **HashiCorp Vault:** secrets at rest (self-hosted compose service). **[VERIFY]** prod
  deployment.
- **LiteLLM:** Python library; routes to providers directly — not a separate hosted
  subprocessor.
- **Observability:** Grafana/Loki endpoints appear in structured logs
  (`backend/app/core/metrics.py`). Logs observed during testing contained metadata and URLs,
  not message content. **[VERIFY]** whether metrics ship to an external service and whether
  any contain customer content.

---

## 4. Data retention

### 4.1 Backups — the 6.1 policy (`docker/backup/backup.sh`)

- **Schedule:** nightly via cron (`CRON_SCHEDULE`, default 03:00 UTC) plus one backup on
  container start (`BACKUP_ON_START`, default true).
- **Retention:** **daily backups pruned after 30 days; weekly backups pruned after 90 days**
  (`retention_prune daily 30`, `retention_prune weekly 90`, `backup.sh:91-92`). Weekly
  archives are written on Sundays under `weekly/<YEAR>/W<week>/`.
- **Contents:** Postgres logical dump (`pg_dump -Fc`) + Qdrant collection snapshot.
  **Redis caches and uploaded source files are NOT backed up.**
- **DPA implication:** customer content in backups is retained up to **30 days (daily)** or
  **90 days (weekly)** in object storage. Org offboarding (§5) deletes live data but does NOT
  retroactively remove prior backups — they age out on schedule. Both facts must be disclosed
  in the Privacy Policy and offboarding terms.

### 4.2 Application-store retention

- **Redis caches (ephemeral):** session history 1h, knowledge cache 5 min, optimization
  cache 10 min (`backend/.env.example:100-103`).
- **Postgres / Qdrant / uploads:** retained indefinitely until explicitly deleted
  (offboarding, or manual per-org/user deletion). No automatic purging of active data.
- **Provider-side retention:** LLM providers retain prompts/outputs on their own schedules —
  see Section 6. Scout cannot independently guarantee deletion at those providers.

---

## 5. Offboarding / deletion capability — the 6.2 policy

Source: `docs/offboarding.md`, `backend/app/domain/offboarding/service.py`,
`backend/app/api/endpoints/admin.py:111-179`.

- **Two-step confirmation flow** (platform-admin only):
  1. `POST /admin/organizations/{org_id}/offboard` — returns a deletion preview (per-table
     Postgres counts, Qdrant/pgvector points, Redis cache counts, upload file/byte counts)
     plus a signed confirmation token (JWT `type=offboard_confirm`, bound to org + admin,
     15-minute TTL). Deletes nothing.
  2. `POST /admin/organizations/{org_id}/offboard/confirm` with the token — verifies and
     executes the purge, returning a completion report.
- **What is deleted:**
  - **Postgres:** all org-scoped rows in FK-safe order — `messages` (via session subquery),
    `analytics_events`, `daily_analytics`, `llm_usage`, `knowledge_sources`, `policies`,
    `sessions`, `chatbots`, `api_keys`, `audit_logs` (org-scoped), `webhooks`,
    `usage_billing_records`, `users`, then the `organizations` row.
  - **Vectors:** the org's Qdrant points (payload `organization_id` filter) and pgvector
    fallback rows when enabled.
  - **Redis:** org memory (`org_config:*`, `org_policies:*`), session history keys
    (`session:*:history`), the knowledge cache (`knowledge_cache:*` entries whose payloads
    reference the org), and the whole `opt_cache:*` namespace (keys are md5-hashed with no
    org marker; short-TTL, recomputable).
  - **Uploads:** everything under `UPLOAD_DIR/<org_id>/`.
- **Audit-log exception (deliberate and documented):** the offboarding operation itself is
  written to `audit_logs` **before** the purge as a platform-level record
  (`organization_id`/`user_id` NULL, org id + name + admin id in `details`), so it survives
  the purge as immutable proof that deletion occurred.
- **Caveats the legal docs must state:**
  1. Prior **backups** still contain the org's data until they age out (Section 4.1).
  2. **LLM providers** retain prompts/outputs on their own schedules (Section 6) — Scout
     cannot guarantee deletion at those providers.
  3. `usage_billing_records` are deleted, so any **financial settlement must be completed
     before** offboarding (documented as a runbook prerequisite).

---

## 6. Do the configured LLM providers train on submitted data?

**Explicit per-provider analysis — do NOT assume "no" for any of them.** Researched
2026-08-16 from each provider's public policy. **[VERIFY]** each against the live policy
before publishing; provider terms change frequently.

| Provider | Trains on submitted data? | Retention | Notes |
|---|---|---|---|
| **OpenAI** (API) | **No by default.** API inputs/outputs not used to train unless the customer explicitly **opts in**. | Abuse-monitoring logs up to **30 days**, then deleted (longer if legally required). ZDR available for eligible enterprise endpoints. | Regional processing via `us.api` / `eu.api`; system data (account/usage metadata) excluded from residency. |
| **Anthropic** (API / Claude commercial) | **No by default.** Commercial terms state customer content is not used to train models. | Inputs/outputs auto-deleted within ~**30 days**; one 2026 source reports **7 days** for API logs (as of Sep 2025) — **[VERIFY] current window**. Flagged content up to 2 years; trust/safety scores up to 7 years. ZDR available. | Consumer Claude.ai is governed by different terms (opt-out to avoid training). The API track is the relevant one for Scout. |
| **Google Gemini** (API) | **No for paid Gemini API / Vertex AI.** **Free Google AI Studio / unpaid tier MAY use submitted data** to improve Google products, including training; human review possible. | ~**55 days** abuse-monitoring retention (project-adjustable 7/14/28/55). | **Tier matters materially.** If production uses a free-tier Gemini key, data-use differs. EEA/Switzerland/UK: paid-service terms apply even on free tiers. |
| **Together AI** | **No by default.** Data sharing for training is **opt-in**, disabled by default. | **ZDR by default** — inputs/outputs not stored; temporary caching possible. | Organization-level privacy toggles; passthrough models inherit the upstream provider's policy. |
| **Azure OpenAI** | **No.** Prompts/completions/embeddings/training data are never used to train OpenAI, Microsoft, or third-party models. | 30-day abuse-monitoring window. ZDR / modified monitoring available (enterprise agreement). | Data stays in the customer's Azure region; inference models are stateless. |
| **Ollama (local)** | N/A — runs on Scout's own infrastructure; no data transmitted to a third party. | N/A | Only relevant if `OLLAMA_ENABLED` in production. |

### Drafting implications

1. **Every configured provider is no-training-by-default on the API track** — but each
   retains prompts/outputs for abuse monitoring (7–55 days) and none offers Scout a
   contract-level deletion guarantee without a DPA/ZDR arrangement.
2. **Gemini free tier is the one real "trains on data" risk.** Verify the Gemini tier in
   production; if free-tier, either exclude it or disclose the difference.
3. The DPA should name the **actual providers** (not "LiteLLM") and require each to honor
   no-training and to state its retention window.
4. Whether Scout itself may review or store chat content (e.g., for abuse monitoring) should
   be stated explicitly; the codebase has no content-level monitoring, only regex-based
   post-generation safety checks on model output (`response_pipeline.py:66-92`).

---

## 7. Suggested document structure (for counsel)

1. **Privacy Policy**
   - Controller identity + contact
   - Categories of data processed (account data, documents, chat content, usage/analytics)
   - Purposes and lawful bases
   - Subprocessors (Section 3, updated with verified prod list)
   - Storage locations/regions (Section 2, verified)
   - Retention periods (Section 4)
   - Deletion / offboarding rights (Section 5)
   - Training-on-data disclosure (Section 6)
   - Security measures (bcrypt, TLS, RLS, Vault — from `docs/Security Framework.md`)
   - International transfers + safeguards
   - Data subject rights + contact
2. **Terms of Service**
   - Service description, acceptable use (customer data ingestion)
   - Customer obligations (content ownership, lawful use, no personal/sensitive data beyond
     what customer permits)
   - AI output disclaimer, no guarantees on model behavior
   - Billing via Razorpay, overage policy, cancellation
   - Suspension/termination + offboarding procedure
   - Liabilities, warranties, indemnities
3. **Data Processing Agreement (DPA)**
   - Roles: Scout = processor; customer = controller
   - Instructions and purposes of processing (Sections 1–2)
   - Subprocessor list + obligations (Section 3)
   - Transfers and safeguards (Section 2, verified)
   - Retention and deletion (Sections 4–5)
   - Security measures, confidentiality
   - Audit rights, incident notification, liability

---

## 8. Verification checklist — resolve before sending to counsel / publishing

1. **Production cloud/hosting provider + region(s)** for Postgres, Qdrant, Redis, uploads,
   backups (S3), and Vault — none are pinned in the repo.
2. **Which LLM providers are actually enabled in prod** (OpenAI primary; are
   Anthropic/Gemini/Together/Azure keys provisioned? do fallbacks fire?).
3. **Production embedding model** (assumes OpenAI `text-embedding-3-small`).
4. **Payments provider** — codebase is Razorpay; confirm no Stripe in reality.
5. **Gemini API tier** (free vs paid) — training policy differs.
6. **Anthropic API retention window** — current value (30 days vs 7 days).
7. Whether **observability/metrics** leave the environment and contain customer content.
8. Whether production enables **Ollama** (local processing) — affects subprocessor list.
9. Current links/versions of each LLM provider's data-usage policy cited in Section 6.

---

## 9. Source references (codebase)

- `backend/app/api/endpoints/uploads.py` — upload types + local storage layout
- `backend/app/api/endpoints/widget_api.py`, `backend/app/schemas/widget.py` — chat flow
- `backend/app/core/pipeline/response_pipeline.py` — prompt construction, LLM call, safety checks
- `backend/app/core/ai/config.py`, `backend/app/core/ai/router.py` — model map + fallback chain
- `backend/app/core/knowledge/embeddings.py`, `qdrant_store.py`, `pgvector_store.py` — ingestion
- `backend/app/core/billing/` — Razorpay integration
- `docker/backup/backup.sh` — backup schedule + retention (30/90 days)
- `docs/offboarding.md`, `backend/app/domain/offboarding/service.py` — deletion capability
- `backend/.env.example` — config defaults (models, TTLs, feature flags, provider keys)
- `docker/docker-compose*.yml` — storage services and volumes
- `GUIDE.md` — example deployment (Supabase/Upstash/Qdrant Cloud) — not authoritative for prod