# Scout.io Documentation

The docs are organized by audience. If you're an **organization admin**, start
with the client guide; if you're a **developer** integrating Scout.io, start
with the developer portal guide; if you're **operating** the platform, start
with environment setup and the operations section.

## Getting Started

| Doc | Audience | Contents |
|-----|----------|----------|
| [Environment setup](getting-started/environment-setup.md) | Developers, operators | Prerequisites, `setup_env.sh`, `.env` reference, secrets |
| [Local development](getting-started/local-development.md) | Developers | Running backend/frontend/widget locally, SQLite MVP mode, tests |
| [Demo deployment](getting-started/demo-deployment.md) | Developers, operators | Full Docker stack (profiles, services, ports), nginx TLS, seeding |

## Architecture

| Doc | Contents |
|-----|----------|
| [System architecture](architecture/system-architecture.md) | Full platform overview, API surface, pipeline, data model, RLS |
| [Tech stack](architecture/tech-stack.md) | Technology choices and rationale |
| [Data & memory model](architecture/data-model.md) | Memory framework, caching, context optimization |

## Guides (by role)

| Doc | Audience | Contents |
|-----|----------|----------|
| [Client guide](guides/client-guide.md) | Organization admins (non-technical) | Chatbots, knowledge sources, policies, analytics, billing, 2FA, widget embed |
| [Admin guide](guides/admin-guide.md) | Platform administrators | Org management, offboarding, audit logs, system config, health |
| [Developer portal guide](guides/developer-portal-guide.md) | Developers | API reference, API keys, widget integration, testing |

## Operations

| Doc | Contents |
|-----|----------|
| [Staging & deployment](operations/staging-deployment.md) | Staging architecture, deploy process, CI/CD, isolation |
| [Disaster recovery](operations/disaster-recovery.md) | Backup/restore runbook |
| [Monitoring & observability](operations/monitoring-observability.md) | Prometheus/Grafana/Loki/Alertmanager, SLOs, load-testing report |
| [Security & compliance](operations/security-and-compliance.md) | Security model, Vault, RLS, offboarding, privacy brief |

## Integrations

| Doc | Contents |
|-----|----------|
| [LLM providers](integrations/llm-providers.md) | LiteLLM provider config, model tiers, fallbacks, cost tracking |
| [Vector DB & retrieval](integrations/vector-db-qdrant.md) | Qdrant/pgvector, cross-encoder reranker service |
| [Billing (Razorpay)](integrations/billing-razorpay.md) | Plans, subscriptions, checkout, webhooks, limits |
| [Webhooks](integrations/webhooks.md) | Outbound webhook management API, Razorpay inbound webhook, signing |

## Product

| Doc | Contents |
|-----|----------|
| [Roadmap](roadmap.md) | Development phases, progress tracker, product requirements |

## Repository root documents

- [README.md](../README.md) — project overview and quick start
- [CONTRIBUTING.md](../CONTRIBUTING.md) — how to contribute
- [CHANGELOG.md](../CHANGELOG.md) — release history
- [SECURITY.md](../SECURITY.md) — reporting vulnerabilities
- [LICENSE](../LICENSE) — AGPL-3.0

## Archive

`docs/archive/` holds working notes (Issues.md, phase prompts) kept out of the
indexed docs.