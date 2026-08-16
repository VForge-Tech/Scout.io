# LLM Providers & AI Routing

Scout.io abstracts LLM access through **LiteLLM** (`app/core/ai/router.py`),
which lets the platform talk to multiple providers with one interface and
provides primary → fallback → graceful error behavior. This doc covers provider
configuration, model tiers, and the fallback chain.

## Provider support

Backend secrets are read via the Vault-backed `SecretManager` (env fallback in
development). The supported providers map to these env vars (see
`docs/getting-started/environment-setup.md`):

| Provider | Env var | Notes |
|----------|---------|-------|
| OpenAI | `OPENAI_API_KEY` | Default for embeddings + chat |
| Anthropic | `ANTHROPIC_API_KEY` | Claude models |
| Google Gemini | `GEMINI_API_KEY` | `gemini/*` model ids |
| Together AI | `TOGETHER_API_KEY` | `together/*` model ids |
| Azure OpenAI | `AZURE_OPENAI_API_KEY` (+ endpoint/deployment vars) | `azure/*` model ids |
| Ollama (local) | `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDING_MODEL` | Local/offline models |

Optional secrets in `.env.example`: `openai_api_key`, `anthropic_api_key`,
`together_api_key`, `gemini_api_key`, `azure_openai_api_key`. Only the
providers you configure need keys; at least one is required for generation.

## Model tiers

Chatbots expose a `behaviour` field (`fast` / `balanced` / `accurate`) that
maps to configured model ids:

| Behaviour | Model (default) | Use case |
|-----------|-----------------|----------|
| `fast` | `gpt-3.5-turbo` | Quick, cost-effective |
| `balanced` | `gpt-4o-mini` | Default best balance |
| `accurate` | `gpt-4o` | Complex reasoning, highest quality |

Config in `backend/.env`:

```env
FAST_LLM_MODEL=gpt-3.5-turbo
BALANCED_LLM_MODEL=gpt-4o-mini
ACCURATE_LLM_MODEL=gpt-4o
FALLBACK_MODELS=["claude-3-haiku-20240307", "gemini/gemini-1.5-flash"]
```

## Embeddings

Embeddings are produced through the same LiteLLM abstraction
(`app/core/knowledge/embeddings.py`):

```env
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

For local/offline use, enable Ollama embeddings (`OLLAMA_ENABLED=true`,
`OLLAMA_EMBEDDING_MODEL=nomic-embed-text`). The `pgvector` and `Qdrant` stores
accept any embedding of the configured dimension.

## Fallback chain & graceful degradation

`AIRouter.generate()` implements a primary → fallback chain:

1. Try the primary model for the chatbot's behaviour tier.
2. On failure, step through `FALLBACK_MODELS` in order.
3. If everything fails, return a graceful error response rather than raising —
   the pipeline degrades, it never hard-fails the request.

Failure/fallback events increment the `scout_llm_fallback_triggers_total`
Prometheus counter (see `docs/operations/monitoring-observability.md`), so a
provider outage is visible in the LLM dashboard and alert rules
(`LLMFallbackRateHigh`).

## Cost tracking & usage

Every generation records an `LLMUsage` row (tokens from the provider, or an
estimate via `count_tokens`), including the model actually used after
fallbacks. Estimated cost is computed in `app/core/billing/pricing.py`
(paise-per-1K) and aggregated monthly by the billing Celery task — see
`docs/integrations/billing-razorpay.md`.

## Mock mode (load testing)

`MOCK_LLM=true` replaces provider calls with deterministic canned responses
(120 ms sleep, hash-seeded pseudo-vectors for embeddings) so the full pipeline
can be exercised against real infra at zero API cost. Used by the load-testing
suite (`load-tests/`); see `docs/operations/monitoring-observability.md`.