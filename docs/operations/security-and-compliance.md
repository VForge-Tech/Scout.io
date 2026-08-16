# Scout.io Security & Compliance

> This document merges the previous Security Framework, Vault Production Setup,
> Offboarding, and Privacy Drafting Brief docs into a single reference. See also
> `docs/operations/disaster-recovery.md` (backup/restore) and
> `docs/architecture/system-architecture.md` (RLS and multi-tenant isolation). 

## Overview 

The Scout.io Security Framework establishes the security principles, validation mechanisms, threat mitigation strategies, and data protection policies implemented throughout the platform. 

Security is not implemented as an independent component within Scout.io. Instead, every architectural component must inherit the security requirements defined within this document. 

The Security Framework is responsible for: 

- Organization isolation. 

- Authentication. 

- Authorization. 

- Session security. 

- API security. 

- Knowledge security. 

- AI security. 

- Deployment security. 

- Data protection. 

- Threat mitigation. 

- Response sanitization. 

- Infrastructure security. 

Security should always take precedence over: 

- Features. 

- Performance optimizations. 

- Architectural conveniences. 

- Implementation simplicity. 

## Security Philosophy 

Scout.io follows five fundamental security principles. 

### Zero Trust Architecture 

No component should automatically trust: 

- Requests. 

- Responses. 

- Organizations. 

- Sessions. 

- Knowledge sources. 

- Retrieved contexts. 

- AI outputs. 

- Synchronization workflows. 

Everything must undergo validations before processing. 

### Least Privilege Principle 

Every component should receive only the permissions required to perform its responsibilities. 

Examples include: 

- Organizations access organizational resources only. 

- Chatbots access chatbot resources only. 

- Sessions access session resources only. 

- APIs access authorized resources only. 

Excessive permissions should always be avoided. 

### Defense in Depth 

Security mechanisms should exist across multiple layers including: 

```text id=“sec001” Requests 

#### ↓ 

Authentication 

#### ↓ 

Authorization 

#### ↓ 

Organization Validation 

↓ 

Policy Validation 

#### ↓ 

Knowledge Validation 

#### ↓ 

AI Validation 

#### ↓ 

Response Validation 

↓ 

Response Sanitization 

↓ 

Final Response 

No individual security mechanism should be considered sufficient in isolation. 

--- 

### Organization Isolation 

Organization-level isolation remains mandatory throughout Scout.io. 

No organization should have visibility into: 

- Knowledge sources. 

- Sessions. 

- Configurations. 

- Policies. 

- Analytics. 

- Deployments. 

belonging to other organizations. 

--- 

### Graceful Security Handling 

Security failures should always fail gracefully. 

Examples include: 

- Unauthorized requests. 

- Invalid sessions. 

- Expired tokens. 

- Restricted responses. 

- Policy violations. 

Security failures should never expose: 

- Internal metadata. 

- Stack traces. 

- Infrastructure details. 

- Sensitive information. 

--- 

## Security Architecture 

```text id="sec002" Incoming Request | Authentication | Authorization | Organization Validation | Resource Validation | Policy Validation | Security Validation | Business Processing | Response Validation | Response Sanitization | Final Response 

Every request must undergo this security workflow. 

## Threat Model 

The Scout.io Security Framework protects against: 

### External Threats 

- Unauthorized access. 

- API abuse. 

- Session hijacking. 

- Prompt injection attacks. 

- Rate limit abuse. 

- Data exposure attempts. 

### Organizational Threats 

- Cross-organization access. 

- Improper configurations. 

- Knowledge source abuse. 

- Privilege escalations. 

### AI Threats 

- Hallucinations. 

- Prompt injections. 

- Context poisoning. 

- Information leakage. 

- Response manipulations. 

### Infrastructure Threats 

- Deployment failures. 

- Misconfigurations. 

- Resource exhaustion. 

- Service abuse. 

Security mechanisms should continuously evolve alongside emerging threats. 

## Authentication Framework 

The authentication framework is responsible for: 

- Identity validation. 

- Token management. 

- Session validations. 

- Future OAuth integrations. 

Supported mechanisms include: 

- JWT Authentication. 

- OAuth Authentication. 

- API Authentication. 

Future support includes: 

- Multi-factor authentication. 

- Enterprise Single Sign-On. 

- Hardware-backed authentication. 

Authentication alone must never grant resource access. 

## Authorization Framework 

Authorization determines whether authenticated entities may access requested resources. 

Examples include: 

```text id=“sec003” Authenticated? 

↓ 

YES 

↓ 

Authorized? 

↓ 

YES 

↓ 

Organization Validation 

↓ 

Resource Validation 

↓ 

Access Granted 

#### NO 

#### ↓ 

#### Access Denied 

##### Authorization policies remain mandatory throughout all services. 

--- 

## Organization Isolation Strategies 

Every resource within Scout.io belongs to an organization. 

Examples include: 

```text id="sec004" Organization 

##### ↓ 

Chatbots 

↓ 

Sessions 

##### ↓ 

Policies 

##### ↓ 

Knowledge Sources 

##### ↓ 

Analytics 

↓ 

Deployments 

Mandatory requirements include: 

- Resource ownership validations. 

- Organization-level access controls. 

- Independent policy management. 

- Independent session management. 

Cross-organizational access must remain impossible under normal operating conditions. 

## API Security Framework 

Every API should implement: 

- Authentication. 

- Authorization. 

- Rate limiting. 

- Request validations. 

- Input sanitization. 

- API versioning. 

Examples include: 

```text id=“sec005” API Request 

#### ↓ 

Rate Limiting 

#### ↓ 

Authentication 

#### ↓ 

Authorization 

#### ↓ 

Validation 

#### ↓ 

Processing 

#### ↓ 

Sanitization 

↓ 

#### Response 

All APIs should remain: 

- Secure. 

- Versioned. 

- Documented. 

- Extensible. 

--- 

## Session Security 

The Session Security Framework is responsible for: 

- Session validations. 

- Session storage policies. 

- Session isolation. 

- Session expiration policies. 

Organizations should configure: 

- Session durations. 

- Storage policies. 

- Retention configurations. 

Examples include: 

```text id="sec006" Session Created 

↓ 

Validation 

↓ 

Retention Policies 

↓ 

##### Expiration 

##### ↓ 

##### Deletion 

##### ↓ 

##### Completion 

Expired sessions should never remain accessible. 

## Knowledge Security 

Knowledge sources must undergo: 

- Source validations. 

- Integrity validations. 

- Synchronization validations. 

- Policy validations. 

Examples include: 

```text id=“sec007” Knowledge Source 

↓ 

Validation 

↓ 

Synchronization 

↓ 

Metadata Validation 

#### ↓ 

Embedding Generation 

#### ↓ 

Knowledge Indexing 

↓ 

#### Completion 

Knowledge retrieval should always remain policy-aware. 

--- 

## AI Security Framework 

The AI Security Framework is responsible for protecting: 

- Organizational knowledge. 

- Generated responses. 

- Retrieved contexts. 

- Session information. 

AI workflows should protect against: 

- Prompt injections. 

- Context poisoning. 

- Sensitive information leakage. 

- Hallucinations. 

- Unauthorized responses. 

Examples include: 

```text id="sec008" Question 

↓ 

Policy Validation 

##### ↓ 

Knowledge Validation 

##### ↓ 

AI Routing 

↓ 

##### Response Generation 

##### ↓ 

##### Response Validation 

##### ↓ 

##### Response Sanitization 

##### ↓ 

##### Final Response 

AI providers should never directly expose organizational information. 

## Prompt Injection Protection 

The platform should actively mitigate: 

- Instruction overrides. 

- Context manipulations. 

- Knowledge source abuses. 

- System prompt exposures. 

Examples include: 

```text id=“sec009” Customer Input 

↓ 

Validation 

↓ 

Policy Checks 

↓ 

Restricted Patterns 

↓ 

Context Isolation 

↓ 

AI Routing 

↓ 

Response Generation 

Retrieved contexts should never override organizational policies. 

--- 

## Response Sanitization Framework 

Before responses are delivered, they must undergo: 

- Metadata sanitization. 

- Security validations. 

- Policy validations. 

- Formatting validations. 

Responses must never expose: 

- Internal prompts. 

- Provider information. 

- Organizational metadata. 

- Infrastructure details. 

- Synchronization information. 

Only the final response should remain visible to customers. 

--- 

## Data Protection Policies 

Scout.io intentionally follows minimal data storage principles. 

The platform primarily stores: 

- Organizational metadata. 

- Configurations. 

- Sessions. 

- Embeddings. 

- Analytics metadata. 

Organizations remain the owners of: 

- Knowledge sources. 

- Organizational information. 

- Policies. 

- Configurations. 

Unnecessary data duplication should always be avoided whenever feasible. 

--- 

## Encryption Requirements 

Sensitive information should always remain encrypted. 

Examples include: 

- Access tokens. 

- API credentials. 

- Organizational secrets. 

- Session information. 

- Deployment credentials. 

Encryption should be implemented for: 

- Data at rest. 

- Data in transit. 

Sensitive information should never appear within: 

- Logs. - Analytics. 

- Responses. 

- Public APIs. 

--- 

## Rate Limiting Policies 

The Rate Limiting Framework protects against: 

- API abuse. 

- Resource exhaustion. 

- Malicious traffic. 

- Automated attacks. 

Examples include: 

```text id="sec010" Incoming Requests 

##### ↓ 

Rate Limiting 

##### ↓ 

Allowed? 

↓ 

YES 

↓ 

Processing 

---------------------- 

NO 

##### ↓ 

Graceful Rejection 

Rate limiting policies should remain configurable internally without affecting organizational experiences. 

## Logging Policies 

Logging should prioritize: 

- Security. 

- Observability. 

- Privacy. 

Logs may contain: 

- Request identifiers. 

- Performance statistics. 

- Synchronization statistics. 

- Failure information. 

Logs must never contain: 

- Passwords. 

- Organizational secrets. 

- API credentials. 

- Complete customer conversations. 

- Internal prompts. 

Sensitive information should remain excluded from all logging mechanisms. 

## Deployment Security 

Deployment responsibilities include: 

- Configuration validations. 

- Credential protections. 

- Environment isolation. 

- Infrastructure protections. 

Deployment workflows must protect: 

- Organizational configurations. 

- Knowledge sources. 

- Session information. 

- Infrastructure credentials. 

## Failure Handling Strategies 

### Authentication Failures 

```text id=“sec011” Authentication Failed 

↓ 

#### Access Denied 

↓ 

Graceful Response 

#### ↓ 

Completion 

### Authorization Failures 

```text id="sec012" Unauthorized Access 

↓ 

Access Denied 

↓ 

Security Logging 

↓ 

Completion 

### Security Violations 

```text id=“sec013” Policy Violation 

↓ 

Request Blocked 

#### ↓ 

Security Logging 

↓ 

Graceful Response 

↓ 

Completion ``` 

Security failures should never disclose sensitive implementation details. 

## Security Monitoring 

The Security Framework should monitor: 

- Authentication statistics. 

- Authorization failures. 

- Rate limiting statistics. 

- Session statistics. 

- Policy violations. 

- Deployment statistics. 

Future monitoring capabilities include: 

- Threat detection. 

- Anomaly detection. 

- Enterprise auditing. 

- Security analytics. 

## Future Scope 

Future capabilities include: 

- Multi-factor authentication. 

- Enterprise identity management. 

- Security auditing systems. 

- Threat intelligence integrations. 

- Zero-trust enterprise deployments. 

- Hardware-backed security mechanisms. 

Future additions should inherit existing security principles without introducing breaking changes. 

## Security Constraints 

The following constraints remain mandatory throughout Scout.io: 

- Security always takes precedence over feature additions. 

- Organization-level isolation is non-negotiable. 

- Authentication never implies authorization. 

- Responses must undergo validation and sanitization. 

- Sensitive information must never be exposed through APIs, widgets, or analytics. 

- AI providers remain abstracted from organizations and customers. 

- Components must remain independently replaceable. 

- Security failures should fail gracefully. 

- Zero Trust Architecture remains mandatory across all components. 

## Security Philosophy 

The Scout.io Security Framework intentionally treats security as an inherited property rather than an independent service. Every request, response, knowledge source, session, and AI workflow must continuously validate the legitimacy, authorization, and integrity of the operations being performed. 

The objective of the Security Framework is not merely to prevent unauthorized access, but to establish trust boundaries throughout the platform while preserving organizational ownership, privacy, and reliability. 

The success of the Security Framework will not be measured by the absence of failures alone, but by its ability to consistently protect organizational knowledge and customer interactions while remaining invisible to legitimate users. 

This document serves as the authoritative specification for all security principles, policies, validations, and protection mechanisms implemented throughout Scout.io. Future architectural decisions must inherit and preserve the constraints defined within this framework. 


---

## Vault production setup (merged)

> The following section was merged from `docs/Vault_Production_Setup.md`.

# HashiCorp Vault Production Setup for Scout.io

This guide covers setting up HashiCorp Vault in production mode for Scout.io secret management.

## Overview

Scout.io uses HashiCorp Vault as the primary secret store in production. All sensitive configuration (database credentials, API keys, JWT secrets, etc.) is fetched from Vault at application startup.

## Prerequisites

- HashiCorp Vault 1.15+ (Docker image: `hashicorp/vault:1.15`)
- Access to Vault CLI (`vault` command)
- Understanding of Vault concepts: sealing/unsealing, policies, tokens, KV secrets engine

---

## 1. Provision Vault in Production Mode

### Docker Compose (Recommended)

Use the production docker-compose file which includes Vault with file storage backend:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d vault
```

This starts Vault with:
- File backend storage at `/vault/file`
- TLS disabled (terminate TLS at load balancer/reverse proxy)
- Persistent volumes for data and logs

### Kubernetes (Helm)

For Kubernetes deployments, use the official Vault Helm chart:

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  --set "server.ha.enabled=true" \
  --set "server.ha.raft.enabled=true" \
  --set "server.ha.replicas=3" \
  --set "injector.enabled=false" \
  --set "csi.enabled=false"
```

---

## 2. Initialize Vault

### First-time Initialization

```bash
# Initialize Vault (generates root token and unseal keys)
vault operator init -key-shares=5 -key-threshold=3
```

**Critical**: Save the output securely!
- **5 unseal keys** (any 3 required to unseal)
- **1 root token** (full admin access)

Store unseal keys in a secure password manager or split among team members.
Never store all unseal keys in one place.

### Unseal Vault

Vault starts sealed. Unseal it with 3 of the 5 keys:

```bash
vault operator unseal <unseal-key-1>
vault operator unseal <unseal-key-2>
vault operator unseal <unseal-key-3>
```

Verify status:
```bash
vault status
# Should show: Sealed: false
```

### Automated Unsealing (Production)

For production, use auto-unseal with cloud KMS:

- **AWS KMS**: `seal "awskms" { region = "us-east-1", kms_key_id = "..." }`
- **GCP KMS**: `seal "gcpckms" { project = "...", region = "...", key_ring = "...", crypto_key = "..." }`
- **Azure Key Vault**: `seal "azurekeyvault" { client_id = "...", tenant_id = "...", vault_name = "...", key_name = "..." }`

Add to Vault config (`VAULT_LOCAL_CONFIG`):

```json
{
  "seal": {
    "awskms": {
      "region": "us-east-1",
      "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/..."
    }
  }
}
```

---

## 3. Enable KV v2 Secrets Engine

```bash
# Login with root token
export VAULT_TOKEN=<root-token>
vault login

# Enable KV v2 at path 'secret/'
vault secrets enable -path=secret -version=2 kv
```

Verify:
```bash
vault secrets list
# Should show: secret/  kv  kv_2  n/a  n/a
```

---

## 4. Create Application Policy

Create a policy that grants read access to Scout.io secrets:

```bash
# Create policy file
cat > scout-io-policy.hcl <<'EOF'
path "secret/data/scout-io/production/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/scout-io/production/*" {
  capabilities = ["list"]
}
EOF

# Write policy
vault policy write scout-io-app scout-io-policy.hcl
```

---

## 5. Create Application Token

Generate a token with the application policy:

```bash
# Create token with 1-year TTL, renewable
vault token create \
  -policy=scout-io-app \
  -ttl=8760h \
  -renewable=true \
  -display-name="scout-io-production-app"
```

Save the token output - this is your `VAULT_TOKEN` for production.

### Alternative: AppRole Auth (Recommended for Production)

For better security, use AppRole instead of static tokens:

```bash
# Enable AppRole auth method
vault auth enable approle

# Create role for Scout.io
vault write auth/approle/role/scout-io \
  token_policies="scout-io-app" \
  token_ttl=1h \
  token_max_ttl=24h \
  secret_id_ttl=0

# Get Role ID (static, like username)
vault read auth/approle/role/scout-io/role-id

# Generate Secret ID (dynamic, like password - rotate periodically)
vault write -f auth/approle/role/scout-io/secret-id
```

In application, use `VAULT_ROLE_ID` and `VAULT_SECRET_ID` instead of `VAULT_TOKEN`.

---

## 6. Write Application Secrets

Write all required secrets to Vault:

```bash
# Login with a token that has write access
vault login <admin-token>

# Database URL
vault kv put secret/scout-io/production/database_url \
  value="postgresql://user:password@host:5432/dbname"

# Redis URL
vault kv put secret/scout-io/production/redis_url \
  value="redis://default:password@host:6379/0"

# Qdrant
vault kv put secret/scout-io/production/qdrant_url \
  value="https://your-cluster.region.cloud.qdrant.io"
vault kv put secret/scout-io/production/qdrant_api_key \
  value="your-qdrant-api-key"

# JWT Secret (generate with: openssl rand -base64 48)
vault kv put secret/scout-io/production/jwt_secret \
  value="your-super-secret-jwt-key-min-32-chars"

# Celery
vault kv put secret/scout-io/production/celery_broker_url \
  value="redis://default:password@host:6379/1"
vault kv put secret/scout-io/production/celery_result_backend \
  value="redis://default:password@host:6379/1"

# LLM Provider API Keys (optional - only add what you use)
vault kv put secret/scout-io/production/openai_api_key \
  value="sk-your-openai-key"
vault kv put secret/scout-io/production/anthropic_api_key \
  value="sk-ant-your-anthropic-key"
vault kv put secret/scout-io/production/together_api_key \
  value="your-together-key"
vault kv put secret/scout-io/production/gemini_api_key \
  value="your-gemini-key"
vault kv put secret/scout-io/production/azure_openai_api_key \
  value="your-azure-openai-key"

# Webhook secret
vault kv put secret/scout-io/production/webhook_secret \
  value="your-webhook-signing-secret"
```

### Batch Write (Script)

```bash
#!/bin/bash
# write-secrets.sh - Run with appropriate permissions

set -e

VAULT_PATH="secret/scout-io/production"

write_secret() {
  local key=$1
  local value=$2
  vault kv put $VAULT_PATH/$key value="$value"
  echo "Written: $key"
}

# Required secrets
write_secret "database_url" "$DATABASE_URL"
write_secret "redis_url" "$REDIS_URL"
write_secret "qdrant_url" "$QDRANT_URL"
write_secret "qdrant_api_key" "$QDRANT_API_KEY"
write_secret "jwt_secret" "$JWT_SECRET"
write_secret "celery_broker_url" "$CELERY_BROKER_URL"
write_secret "celery_result_backend" "$CELERY_RESULT_BACKEND"

# Optional secrets
[ -n "$OPENAI_API_KEY" ] && write_secret "openai_api_key" "$OPENAI_API_KEY"
[ -n "$ANTHROPIC_API_KEY" ] && write_secret "anthropic_api_key" "$ANTHROPIC_API_KEY"
[ -n "$TOGETHER_API_KEY" ] && write_secret "together_api_key" "$TOGETHER_API_KEY"
[ -n "$GEMINI_API_KEY" ] && write_secret "gemini_api_key" "$GEMINI_API_KEY"
[ -n "$AZURE_OPENAI_API_KEY" ] && write_secret "azure_openai_api_key" "$AZURE_OPENAI_API_KEY"
[ -n "$WEBHOOK_SECRET" ] && write_secret "webhook_secret" "$WEBHOOK_SECRET"

echo "All secrets written successfully"
```

---

## 7. Configure Application for Production

Set these environment variables in your production deployment:

```bash
# Vault connection
export VAULT_ADDR="https://vault.yourdomain.com"  # or http://vault:8200 in-cluster
export VAULT_TOKEN="your-app-token-from-step-5"
# OR for AppRole:
# export VAULT_ROLE_ID="your-role-id"
# export VAULT_SECRET_ID="your-secret-id"

# Deployment environment
export DEPLOYMENT_ENV="production"

# Other config (non-secrets)
export DEBUG=false
export DEPLOYMENT_PROFILE=full
```

---

## 8. Verify Application Can Read Secrets

Test the connection:

```bash
# Test Vault connectivity from app container
docker exec scout-backend vault status

# Test secret read
docker exec scout-backend vault kv get secret/scout-io/production/database_url
```

In application logs, you should see:
```
INFO: Vault is available at https://vault.yourdomain.com
```

---

## 9. Secret Rotation

### Manual Rotation

```bash
# Rotate a secret (creates new version)
vault kv put secret/scout-io/production/openai_api_key \
  value="sk-new-openai-key"

# Application will pick up new version on next startup
# For zero-downtime rotation, implement SIGHUP handler or periodic reload
```

### Automated Rotation (CI/CD)

Add to your deployment pipeline:

```yaml
# GitHub Actions example
- name: Rotate API Keys
  run: |
    vault kv put secret/scout-io/production/openai_api_key value="${{ secrets.OPENAI_API_KEY }}"
    vault kv put secret/scout-io/production/anthropic_api_key value="${{ secrets.ANTHROPIC_API_KEY }}"
    # ... other keys
```

---

## 10. Monitoring & Alerting

### Vault Health Checks

```bash
# Basic health
vault status

# Detailed metrics (enable Prometheus metrics endpoint)
vault monitor
```

### Alert on:
- Vault sealed state
- High latency on secret reads
- Token expiration (monitor token TTL)
- Failed authentication attempts

---

## 11. Backup & Disaster Recovery

### Backup Vault Data

```bash
# For file backend, backup the storage directory
tar -czf vault-backup-$(date +%Y%m%d).tar.gz /path/to/vault/file

# For Raft/HA, use snapshot
vault operator raft snapshot save vault-snapshot-$(date +%Y%m%d).snap
```

### Restore

```bash
# File backend
tar -xzf vault-backup.tar.gz -C /vault/file

# Raft
vault operator raft snapshot restore vault-snapshot.snap
```

---

## 12. Security Checklist

- [ ] Vault running in production mode (not dev mode)
- [ ] Auto-unseal configured with cloud KMS
- [ ] TLS enabled on Vault listener
- [ ] Root token revoked after initial setup
- [ ] Application uses least-privilege policy (read-only to secret/scout-io/production/*)
- [ ] Application token has reasonable TTL and is renewable
- [ ] Audit logging enabled (`vault audit enable file file_path=/vault/logs/audit.log`)
- [ ] Regular secret rotation schedule
- [ ] Backup and restore procedures tested
- [ ] Network policies restrict Vault access to application pods only
- [ ] Unseal keys stored securely (split among team, in password manager)

---

## Troubleshooting

### "Vault is required but not available"

- Check `VAULT_ADDR` is correct and reachable
- Verify Vault is unsealed: `vault status`
- Check network policies/firewall rules

### "Secret not found in Vault"

- Verify secret path: `secret/scout-io/production/<key>`
- Check KV v2 is enabled at `secret/`
- Verify token has correct policy

### "Permission denied"

- Check token policies: `vault token lookup`
- Verify policy allows `read` and `list` on secret path

### Application fails to start in production

- Ensure `DEPLOYMENT_ENV=production` is set
- Check logs for Vault connection errors
- Verify all required secrets exist in Vault
---

## Org offboarding (merged)

> The following section was merged from `docs/offboarding.md`.

# Org Offboarding (Permanent Data Deletion)

## Purpose

Permanently delete an organization and **all** data scoped to it across every
store the platform touches, with an explicit two-step confirmation so this
irreversible action cannot be triggered by accident.

## Flow

1. `POST /api/v1/admin/organizations/{org_id}/offboard` (platform admin only)
   - Returns a deletion **preview** (per-table Postgres counts, Qdrant/pgvector
     points, Redis cache counts, upload file/byte counts) plus a signed
     **confirmation token** (JWT, `type=offboard_confirm`, bound to the org and
     the admin, 15 minute TTL).
   - Deletes nothing.
2. `POST /api/v1/admin/organizations/{org_id}/offboard/confirm` (platform admin
   only) with `{"confirmation_token": "..."}`
   - Verifies the token (must be valid, match this org and this admin).
   - Executes the purge and returns a completion **report**.

The two calls are also audit-logged (`org_offboard_requested` and the
platform-level purge proof).

## What gets deleted

- **Postgres** – every org-scoped row across `messages` (via its sessions),
  `analytics_events`, `daily_analytics`, `llm_usage`, `knowledge_sources`,
  `policies`, `sessions`, `chatbots`, `api_keys`, `audit_logs` (org-scoped
  rows), `webhooks`, `usage_billing_records`, `users`, and finally the
  `organizations` row itself, in child-before-parent order so no FK is
  violated.
- **Vectors** – the org's points in the Qdrant collection, and the pgvector
  fallback rows when `pgvector_enabled`.
- **Redis** – org memory keys (`org_config:*`, `org_policies:*`), session
  history keys (`session:*:history`), the knowledge cache (`knowledge_cache:*`
  entries whose payloads reference the org), and the optimization cache
  (`opt_cache:*` namespace – keys are md5-hashed with no org marker, so the
  whole short-TTL namespace is evicted).
- **Uploads** – everything under `UPLOAD_DIR/<org_id>/`.

## Retention decision (documented)

**Audit logs.** Org-scoped audit-log rows are **purged** as part of the
offboarding – they are org data and the org is permanently leaving the
platform. However, the offboarding operation itself is written to `audit_logs`
**before** the purge as a platform-level record (`organization_id` and
`user_id` are NULL; the org id, org name and initiating admin id live in the
`details` JSON). Because it is not org-scoped, the purge cannot remove it, and
it survives as immutable proof that the deletion happened. This is a deliberate
exception to the purge rule.

**Billing records.** `usage_billing_records` rows are deleted as part of "all
Postgres rows". The FK from billing records to `organizations` is NOT NULL, so
retaining them would make it impossible to delete the org row. Financial
settlement must therefore happen **before** offboarding – the runbook
prerequisite below covers this.

## Runbook prerequisites

1. Confirm the operator genuinely intends permanent deletion.
2. Settle / export any outstanding **financial obligations** (billing records
   are deleted).
3. If any external requirement demands a data export (e.g. customer
   contract), export it before running the confirm step.
4. Confirm the organization name in the preview matches the target org.

## Verification

After offboarding:

- `GET /api/v1/admin/organizations` no longer lists the org.
- `GET /api/v1/admin/audit-logs` still contains the `org_offboarded` proof
  record with `organization_id`/`user_id` NULL and the org id in `details`.

## Scope notes / known gaps

- `usage_billing_records` has **no RLS policy** (it was created in migration
  0008 and was not added to the RLS table list in 0006). This pre-dates
  offboarding; offboarding does not rely on RLS (platform-admin bypass), but
  the gap is noted here for future RLS coverage.
- Deletion is executed in a single transaction for Postgres; Redis/Qdrant/
  uploads are best-effort external stores and are reported in the completion
  report (`deleted.*`) rather than rolled back with the DB.
---

## Privacy drafting brief (merged)

> The following section was merged from `docs/privacy-drafting-brief.md`.

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
| PostgreSQL | Account data, messages, sessions, knowledge sources, policies, audit logs, usage/billing | Compose service `postgres` (volume `postgres_data`). Repo defines no cloud/region; the original setup guide example referenced **Supabase PostgreSQL**. **[VERIFY]** prod host/region |
| Qdrant | Document chunk vectors + text payloads | Compose service `qdrant` (volume `qdrant_data`). The original setup guide example referenced **Qdrant Cloud on GCP** (`CLUSTER.region.gcp.cloud.qdrant.io`). **[VERIFY]** prod host/region |
| Redis | Session history, knowledge cache, optimization cache, org memory | Compose service `redis` (volume `redis_data`). TTLs: session 1h, knowledge cache 5 min, opt cache 10 min. The original setup guide example referenced **Upstash / Redis Cloud**. **[VERIFY]** prod host/region |
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
images published to **GHCR** (`.github/workflows/build.yml`). The original setup guide's example
deployment references **Supabase (Postgres)**, **Upstash (Redis)**, and **Qdrant Cloud (GCP)**.
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

Source: the Offboarding section of this document, `backend/app/domain/offboarding/service.py`,
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
   - Security measures (bcrypt, TLS, RLS, Vault — see this document's Security Framework sections)
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
- `docs/operations/security-and-compliance.md` (Offboarding section), `backend/app/domain/offboarding/service.py` — deletion capability
- `backend/.env.example` — config defaults (models, TTLs, feature flags, provider keys)
- `docker/docker-compose*.yml` — storage services and volumes
- `docs/getting-started/environment-setup.md` — example deployment options (Supabase/Upstash/Qdrant Cloud examples) — not authoritative for prod