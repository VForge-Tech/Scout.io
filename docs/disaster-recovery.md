# Scout.io Disaster Recovery Runbook

## Purpose

Restore a full Scout.io environment (Postgres + Qdrant) from the most recent
nightly backup stored in S3-compatible object storage. This runbook is the
procedure an on-call engineer follows during an incident (data loss, corrupt
volume, failed migration, full environment loss).

**Measured RTO (this build, scratch env, 16 Aug 2026): ~22 seconds** from
`restore.sh --latest` invocation to a fully verified environment (download →
teardown → Postgres restore → Qdrant restore → full stack up).

## Backup architecture

- **What is backed up nightly (03:00 UTC, `CRON_SCHEDULE`, default)**
  - Postgres logical dump: `pg_dump -Fc` (custom format, `--no-owner
    --no-privileges`) of the `scout` database.
  - Qdrant snapshot: created via the Qdrant REST API
    (`POST /collections/{name}/snapshots`), downloaded, and stored.
- **Where**
  - S3-compatible object storage. No provider was present in the repo at
    implementation time, so the integration assumes any S3-compatible endpoint
    (AWS S3, MinIO, Backblaze B2, Google Cloud Storage S3-compat, etc.) via the
    AWS CLI v2. Set `S3_ENDPOINT` accordingly; path-style addressing is used
    (works for MinIO and B2; for AWS S3 leave `S3_ENDPOINT` as
    `https://s3.amazonaws.com`).
  - Object layout (bucket = `S3_BUCKET`, prefix = `S3_PREFIX`, default
    `scout-backups`):
    ```
    scout-backups/daily/20260816T030000Z/postgres.dump
    scout-backups/daily/20260816T030000Z/qdrant.snapshot
    scout-backups/weekly/2026/W33/postgres.dump      # Sundays only
    scout-backups/weekly/2026/W33/qdrant.snapshot
    ```
- **Retention**
  - Daily backups: 30 days.
  - Weekly backups (taken every Sunday): 90 days.
  - Pruning runs as part of the nightly backup job (object mtime based).
- **Container**: `docker/backup/` (`backup.sh`, `restore.sh`, `entrypoint.sh`,
  `Dockerfile`). Built as `scout-backup:latest`. Runs as the `backup` service in
  `docker/docker-compose.prod.yml` (profile `full`); runs once on start
  (`BACKUP_ON_START`, default `true` in the image, set `false` in prod compose)
  and then on the cron schedule.

### Exact data volume locations (from docker-compose.prod.yml / docker-compose.yml)

| Service | Image | Host volume | Container path |
|---------|-------|-------------|----------------|
| postgres | `postgres:16-alpine` | `postgres_data` | `/var/lib/postgresql/data` |
| qdrant | `qdrant/qdrant:latest` | `qdrant_data` | `/qdrant/storage` |
| pgvector (fallback) | `pgvector/pgvector:pg16` | `pgvector_data` | `/var/lib/postgresql/data` |
| ollama | `ollama/ollama:latest` | `ollama_data` | `/root/.ollama` |

Named volumes resolve to `/var/lib/docker/volumes/<project>_<name>/_data` on the
host (project = compose project name, default `scout`). The backup/restore
scripts operate **over the network** (pg_dump over TCP, Qdrant REST API) and do
**not** need host-level access to these volumes — that is why volume location is
informational for DR, but relevant if you ever need to manually inspect
`<project>_postgres_data` or `<project>_qdrant_data`.

## Prerequisites

- Docker + docker compose plugin on the operator host.
- The `scout-backup:latest` image (build once: `docker build -t scout-backup
  docker/backup`).
- Object-store credentials available as env vars (or in `docker/.env`):
  `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, optional
  `S3_REGION` (default `us-east-1`), optional `S3_PREFIX` (default
  `scout-backups`).
- The compose project must be reachable from the restore container's network
  (the wrapper auto-joins `<project>_default`).

## Incident procedure

### 1. Confirm severity and pick a restore point

```bash
# List available daily backups (newest last)
docker run --rm --entrypoint sh scout-backup -c \
  "aws --endpoint-url $S3_ENDPOINT s3 ls s3://$S3_BUCKET/$S3_PREFIX/daily/"
```

Choose the newest timestamp dir (e.g. `20260816T030000Z`), or use `--latest`
to pick it automatically. Only restore an older point if you know the newest
backup is corrupted or you need to roll back to a specific state.

### 2. Run the restore

```bash
# From the repo root. Uses --latest by default when no --timestamp given.
scripts/restore.sh --latest

# Or pin an exact backup:
scripts/restore.sh --timestamp 20260816T030000Z

# Custom compose file / project (e.g. a DR/scratch env):
COMPOSE_FILE="docker/docker-compose.scratch.yml" scripts/restore.sh --latest

# Custom layered compose stack (override the default base+prod):
COMPOSE_FILE="docker/docker-compose.yml docker/docker-compose.staging.yml" scripts/restore.sh --latest
```

The default targets the production stack, which is the base compose layered with
the prod overlay (`docker/docker-compose.yml` + `docker/docker-compose.prod.yml`).
`COMPOSE_FILE` accepts a space-separated `-f` list for layered stacks.

The script:
1. Downloads `postgres.dump` + `qdrant.snapshot` for the chosen timestamp.
2. Stops and removes the current stack and **deletes the `postgres_data` and
   `qdrant_data` volumes** (full wipe — the restore container stays attached to
   the compose network, which is why it does not use `compose down`).
3. Starts `postgres` + `qdrant`, waits for Postgres health.
4. `pg_restore --clean --if-exists --no-owner` into Postgres.
5. Copies the snapshot into the qdrant container's `/qdrant/snapshots/`,
   deletes any existing collection (recover refuses to overwrite), then
   `PUT /collections/{name}/snapshots/recover` with `file://` location.
6. Runs `alembic upgrade head` (schema migrations newer than the backup) if the
   compose file has a `backend` service.
7. Brings up the full stack and reports completion.

> **Non-goal**: Redis, Vault and other services are *not* part of the backup
> (Redis is a cache; Vault holds secrets re-provisionable from source). Only
> Postgres + Qdrant are the durable state.

### 3. Verify

```bash
# Postgres
docker exec <project>-postgres-1 psql -U scout -d scout -t \
  -c "SELECT count(*) FROM organizations;"

# Qdrant collection exists + has points
curl -s http://localhost:6333/collections/scout_knowledge \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["points_count"])'

# Application smoke
curl -sf http://localhost:8000/health/ready && echo OK
```

### 4. Record the incident

Log the incident timestamp, chosen restore point, RTO observed, and any data
newer than the backup that was lost (the backup is nightly, so up to ~24h of
post-backup writes are outside the RPO). Alert/notify per the incident plan.

## Expected RTO / RPO

| Metric | Value |
|--------|-------|
| RTO (measured) | ~22 s for Postgres + Qdrant on a scratch env |
| RPO (scheduled) | Up to 24 h (nightly backup); on-demand backup possible via `docker run --rm --entrypoint sh scout-backup /scripts/backup.sh` |

## DR test procedure (scratch environment)

Validated 16 Aug 2026 with `docker/docker-compose.scratch.yml` (Postgres +
Qdrant + MinIO + backup). To reproduce:

```bash
# 1. Start scratch stack
docker compose -f docker/docker-compose.scratch.yml -p scouttest up -d

# 2. Seed data
docker exec scouttest-postgres-1 psql -U scout -d scout -c \
  "CREATE TABLE organizations (...); INSERT ...;"
docker cp docker/backup/seed_scratch.sh scouttest-backup-1:/tmp/seed.sh
docker exec scouttest-backup-1 sh /tmp/seed.sh

# 3. Run a backup
docker exec scouttest-backup-1 sh /scripts/backup.sh

# 4. Simulate disaster + restore (measure elapsed time)
time docker run --rm --network scouttest_default \
  -v /var/run/docker.sock:/var/run/docker.sock:ro -v "$PWD:/app:ro" \
  -e S3_ENDPOINT=http://minio:9000 -e S3_BUCKET=scout-backups \
  -e S3_ACCESS_KEY=scoutbackup -e S3_SECRET_KEY=scoutbackup-secret \
  -e S3_REGION=us-east-1 -e S3_PREFIX=scout-backups -e PROJECT=scouttest \
  -e COMPOSE_FILE=/app/docker/docker-compose.scratch.yml \
  -e POSTGRES_HOST=postgres -e POSTGRES_USER=scout \
  -e POSTGRES_PASSWORD=changeme -e POSTGRES_DB=scout \
  -e QDRANT_URL=http://qdrant:6333 -e QDRANT_COLLECTION=scout_knowledge \
  scout-backup /scripts/restore.sh --compose-file /app/docker/docker-compose.scratch.yml \
  --project scouttest --latest

# 5. Verify counts (see "Verify" above)
```

## Operations notes

- **Restore refuses to overwrite an existing Qdrant collection** — the restore
  script deletes the target collection first. Never restore while the original
  environment is still serving (this script wipes the datastore volumes as part
  of the procedure; point it at a fresh/scratch project to restore into an
  isolated environment, e.g. `-p scoutrestore`).
- **Object-store provider assumption**: the team had no S3 provider wired into
  the repo. The integration uses the AWS CLI v2 against any S3-compatible
  endpoint. Provision a bucket + access key in your chosen provider and set the
  `S3_*` env vars. MinIO was used for validation.
- **Timing**: nightly job default 03:00 UTC; adjust with
  `BACKUP_CRON_SCHEDULE`. Weekly archive only on Sundays.
- **Backup image** needs the compose network to reach `postgres`/`qdrant` (it
  is defined inside the compose project so it shares the default network). The
  restore wrapper joins `<project>_default` automatically.