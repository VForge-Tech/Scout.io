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