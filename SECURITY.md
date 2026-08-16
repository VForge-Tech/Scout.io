# Security Policy

## Supported versions

Security fixes are applied to the current release. Scout.io is in active
development (pre-1.0); only the latest `main` and the latest tagged release
receive security updates.

## Reporting a vulnerability

Do **not** open a public GitHub issue for security vulnerabilities. Report
privately to the maintainers:

- **Email**: security@scout.io
- **Subject prefix**: `[SECURITY]` (so the report is triaged first)

Please include:

1. A description of the vulnerability and its impact (who can exploit it, and
   what they gain).
2. Steps to reproduce, including the affected endpoint, input, and versions.
3. Any suggested fix, if you have one.

You should receive an acknowledgment within 3 business days. We will work on a
fix, release it, and disclose responsibly once it ships. If you prefer, you can
report anonymously via a throwaway account — the important thing is that the
report reaches the maintainers privately.

## Security posture

Scout.io is a multi-tenant platform; tenant data isolation is the top security
concern. The relevant safeguards (and their docs) are:

- **Row-Level Security (RLS)** in Postgres as a database-level backstop under
  application-level org filtering. See
  `docs/architecture/system-architecture.md`.
- **Application-level org isolation** enforced in every org-scoped query
  (dependency `get_db_with_org` sets `app.current_org_id` per request).
- **JWT auth** (access + refresh), **TOTP MFA** mandatory for platform admins,
  single-use recovery codes. See `docs/operations/security-and-compliance.md`.
- **API keys** (`X-API-Key`, bcrypt-hashed) for developer access.
- **Secret management** via HashiCorp Vault (`SecretManager` with env fallback
  in development only); secrets are never committed.
- **Response sanitization** (provider/model names, API keys) and adversarial
  prompt-injection test coverage (22 tests).
- **Rate limiting** per IP and per organization (see
  `backend/.env.example` / `app/core/rate_limit.py`).
- **Webhook signature verification** (HMAC) for outgoing webhooks and inbound
  Razorpay events.
- **Audit logging** of sensitive actions; **org offboarding** performs full
  permanent deletion with proof-of-deletion audit entries.

## Reporting expectations

- We will acknowledge within 3 business days.
- We will keep you informed of progress on a fix.
- We will not release details of the vulnerability until a fix is deployed
  (coordinated disclosure).
- Safe-harbor: researchers testing in a controlled, non-production environment
  who report in good faith are welcome.

## Non-security issues

For general bugs and feature requests, use the GitHub issue tracker — not this
channel.