#!/usr/bin/env bash
# Scout.io full-environment restore from a backup timestamp.
#
# Usage:
#   restore.sh --timestamp <TS> [--compose-file <path>] [--project <name>] [--latest]
#
# <TS> is the backup timestamp like 20260815T030000Z (taken from the object key).
# With --latest, the most recent daily backup found in the bucket is used.
#
# Steps:
#   1. Locate + download the Postgres dump and Qdrant snapshot from object storage.
#   2. Tear down the existing stack (volumes removed => data volumes recreated empty).
#   3. Start only the datastores (postgres, qdrant) and wait until healthy.
#   4. Restore Postgres via pg_restore.
#   5. Restore the Qdrant collection from the snapshot.
#   6. Run alembic migrations forward (catches schema drift past the backup).
#   7. Start the full stack and run a health/verify pass.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT}/docker/docker-compose.yml}"
PROJECT="${PROJECT:-scout}"
TIMESTAMP=""
LATEST=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --timestamp) TIMESTAMP="$2"; shift 2 ;;
    --latest) LATEST=true; shift ;;
    --compose-file) COMPOSE_FILE="$2"; shift 2 ;;
    --project) PROJECT="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Config (mirrors backup.sh defaults)
: "${S3_ENDPOINT:?S3_ENDPOINT required}"
: "${S3_BUCKET:?S3_BUCKET required}"
: "${S3_ACCESS_KEY:?S3_ACCESS_KEY required}"
: "${S3_SECRET_KEY:?S3_SECRET_KEY required}"
: "${POSTGRES_HOST:=postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:=scout}"
: "${POSTGRES_PASSWORD:=changeme}"
: "${POSTGRES_DB:=scout}"
: "${QDRANT_URL:=http://qdrant:6333}"
: "${QDRANT_COLLECTION:=scout_knowledge}"

S3_PREFIX="${S3_PREFIX:-scout-backups}"
export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
export AWS_DEFAULT_REGION="${S3_REGION:-us-east-1}"
AWS="aws --endpoint-url ${S3_ENDPOINT}"

if [ "$LATEST" = true ] && [ -z "$TIMESTAMP" ]; then
  TIMESTAMP="$($AWS s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/daily/" 2>/dev/null \
    | awk '{print $2}' | sed 's#/$##' | sort | tail -1)"
  echo "[$(date -u +%FT%TZ)] latest daily backup dir: $TIMESTAMP"
fi
if [ -z "$TIMESTAMP" ]; then
  echo "usage: restore.sh --timestamp <TS> | --latest" >&2; exit 2
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="/backup/restore-${STAMP}"
mkdir -p "$WORK"
PG_DUMP="${WORK}/postgres.dump"
QDRANT_SNAP="${WORK}/qdrant.snapshot"

# --- 1. Download --------------------------------------------------------------
DAILY_KEY="${S3_PREFIX}/daily/${TIMESTAMP}/"
echo "[$(date -u +%FT%TZ)] downloading ${DAILY_KEY}"
$AWS s3 cp "s3://${S3_BUCKET}/${DAILY_KEY}postgres.dump" "$PG_DUMP" --only-show-errors
$AWS s3 cp "s3://${S3_BUCKET}/${DAILY_KEY}qdrant.snapshot" "$QDRANT_SNAP" --only-show-errors
echo "[$(date -u +%FT%TZ)] downloaded pg dump ($(du -h "$PG_DUMP" | cut -f1)) + qdrant snapshot ($(du -h "$QDRANT_SNAP" | cut -f1))"

# COMPOSE_FILE may be one path or several (`-f` list, space separated) so a
# layered stack (docker-compose.yml + docker-compose.prod.yml) can be restored.
COMPOSE_ARGS=()
for _f in $COMPOSE_FILE; do COMPOSE_ARGS+=(-f "$_f"); done
COMPOSE=(docker compose "${COMPOSE_ARGS[@]}" -p "$PROJECT")

# --- 2. Tear down existing stack (keep the compose network alive — this restore
#        container is attached to it and must keep reaching postgres/qdrant) ----
echo "[$(date -u +%FT%TZ)] tearing down stack (data volumes will be wiped)"
"${COMPOSE[@]}" stop 2>/dev/null || true
"${COMPOSE[@]}" rm -f 2>/dev/null || true
docker volume rm "${PROJECT}_postgres_data" "${PROJECT}_qdrant_data" 2>/dev/null || true
echo "[$(date -u +%FT%TZ)] data volumes removed"

# --- 3. Start datastores first ------------------------------------------------
echo "[$(date -u +%FT%TZ)] starting postgres + qdrant"
"${COMPOSE[@]}" up -d postgres qdrant 2>/dev/null || "${COMPOSE[@]}" up -d
# wait for postgres health
for _ in $(seq 1 60); do
  if docker inspect -f '{{.State.Health.Status}}' "${PROJECT}-postgres-1" 2>/dev/null | grep -q healthy; then break; fi
  sleep 2
done
docker inspect -f '{{.State.Health.Status}}' "${PROJECT}-postgres-1" | grep -q healthy || { echo "postgres not healthy" >&2; exit 1; }

# --- 4. Restore Postgres -------------------------------------------------------
echo "[$(date -u +%FT%TZ)] restoring Postgres"
PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
    -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --clean --if-exists --no-owner --no-privileges \
    "$PG_DUMP"

# --- 5. Restore Qdrant collection ----------------------------------------------
echo "[$(date -u +%FT%TZ)] restoring Qdrant collection ${QDRANT_COLLECTION}"
# Qdrant recovers from a snapshot file via PUT /collections/{c}/snapshots/recover
# with a file:// location. Two constraints: the file must live under the qdrant
# container's /qdrant/snapshots dir, and recovery refuses to overwrite an
# existing collection, so we delete the target collection first (it was just
# wiped by the volume teardown anyway).
QD_CONTAINER="$(docker compose "${COMPOSE_ARGS[@]}" -p "$PROJECT" ps -q qdrant 2>/dev/null | head -1)"
if [ -z "$QD_CONTAINER" ]; then
  echo "qdrant container not found" >&2; exit 1
fi
SNAP_FILE="qdrant-${TIMESTAMP}.snapshot"
docker exec "$QD_CONTAINER" mkdir -p /qdrant/snapshots
docker cp "$QDRANT_SNAP" "${QD_CONTAINER}:/qdrant/snapshots/${SNAP_FILE}"
# Best-effort delete (404 if it never existed after the wipe is fine).
curl -sf -X DELETE "${QDRANT_URL}/collections/${QDRANT_COLLECTION}" >/dev/null 2>&1 || true
curl -sf -X PUT "${QDRANT_URL}/collections/${QDRANT_COLLECTION}/snapshots/recover" \
  -H 'Content-Type: application/json' \
  -d "{\"location\": \"file:///qdrant/snapshots/${SNAP_FILE}\"}" >/dev/null
echo "[$(date -u +%FT%TZ)] qdrant collection restored from ${SNAP_FILE}"

# --- 6. Migrations forward -------------------------------------------------------
# Only if the compose file has a backend service (scratch/DR compose files may
# not). In production this runs any migrations newer than the backup's schema.
if docker compose "${COMPOSE_ARGS[@]}" -p "$PROJECT" config --services 2>/dev/null | grep -qx backend; then
  echo "[$(date -u +%FT%TZ)] running alembic migrations"
  docker compose "${COMPOSE_ARGS[@]}" -p "$PROJECT" run --rm --no-deps backend alembic upgrade head
else
  echo "[$(date -u +%FT%TZ)] no backend service in compose; skipping alembic"
fi

# --- 7. Bring up the stack + verify ---------------------------------------------
echo "[$(date -u +%FT%TZ)] starting full stack"
"${COMPOSE[@]}" up -d --remove-orphans
sleep 5
echo "[$(date -u +%FT%TZ)] restore complete"

rm -rf "$WORK"