#!/usr/bin/env bash
# Scout.io nightly backup: pg_dump of Postgres + Qdrant collection snapshot,
# both uploaded to an S3-compatible object store with retention:
#   - daily backups retained 30 days
#   - weekly backups retained 90 days
set -euo pipefail

echo "[$(date -u +%FT%TZ)] backup start"

: "${S3_ENDPOINT:?S3_ENDPOINT required (e.g. https://s3.amazonaws.com or http://minio:9000)}"
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

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DOW="$(date -u +%u)"   # 1=Mon .. 7=Sun
PG_DUMP="/backup/postgres.dump"
QDRANT_SNAP="/backup/qdrant.snapshot"
QDRANT_SNAP_NAME=""
S3_PREFIX="${S3_PREFIX:-scout-backups}"

mkdir -p /backup
export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
export AWS_DEFAULT_REGION="${S3_REGION:-us-east-1}"
AWS="aws --endpoint-url ${S3_ENDPOINT}"

# --- 1. Postgres logical dump (custom format) ---------------------------------
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -Fc --no-owner --no-privileges \
    -f "$PG_DUMP"
echo "[$(date -u +%FT%TZ)] pg_dump ok: $(du -h "$PG_DUMP" | cut -f1)"

# --- 2. Qdrant snapshot via REST API ------------------------------------------
# POST /collections/{name}/snapshots creates a snapshot server-side (stored in
# /qdrant/storage/snapshots) and returns its name; we then download it via
# GET /collections/{name}/snapshots/{snapshot}.
SNAP_JSON="$(curl -sf -X POST "${QDRANT_URL}/collections/${QDRANT_COLLECTION}/snapshots" -H 'Content-Type: application/json' -d '{"wait": true}')"
QDRANT_SNAP_NAME="$(echo "$SNAP_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["name"])')"
curl -sf "${QDRANT_URL}/collections/${QDRANT_COLLECTION}/snapshots/${QDRANT_SNAP_NAME}" -o "$QDRANT_SNAP"
echo "[$(date -u +%FT%TZ)] qdrant snapshot ok: ${QDRANT_SNAP_NAME} ($(du -h "$QDRANT_SNAP" | cut -f1))"

# --- 3. Upload to object storage ----------------------------------------------
# Daily: s3://<bucket>/<prefix>/daily/<STAMP>/  (STAMP = UTC timestamp, e.g.
# 20260816T105739Z). Each day's directory holds postgres.dump + qdrant.snapshot;
# retries within a day produce a new directory instead of overwriting.
DAILY_KEY="${S3_PREFIX}/daily/${STAMP}/"
$AWS s3 cp "$PG_DUMP" "s3://${S3_BUCKET}/${DAILY_KEY}" --only-show-errors
$AWS s3 cp "$QDRANT_SNAP" "s3://${S3_BUCKET}/${DAILY_KEY}" --only-show-errors
echo "[$(date -u +%FT%TZ)] uploaded daily ${DAILY_KEY}"

# Weekly: on Sunday (DOW=7) also archive under weekly/<ISO-year>/W<week>/
if [ "$DOW" = "7" ]; then
  WEEK_KEY="${S3_PREFIX}/weekly/$(date -u +%Y)/W$(date -u +%V)/"
  $AWS s3 cp "$PG_DUMP" "s3://${S3_BUCKET}/${WEEK_KEY}" --only-show-errors
  $AWS s3 cp "$QDRANT_SNAP" "s3://${S3_BUCKET}/${WEEK_KEY}" --only-show-errors
  echo "[$(date -u +%FT%TZ)] uploaded weekly ${WEEK_KEY}"
fi

# --- 4. Retention --------------------------------------------------------------
# Prune daily objects older than 30 days, weekly older than 90 days. The AWS CLI
# lists objects as "<date> <time> <size> <key>"; we parse the object mtime and
# delete anything whose age exceeds the window. Pruning the directory prefix
# removes both the .dump and .snapshot inside it.
retention_prune() {
  local subdir="$1"   # daily | weekly
  local max_days="$2"
  $AWS s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/${subdir}/" --recursive 2>/dev/null \
    | awk -v max="${max_days}" '
        NF >= 4 {
          # mtime is "YYYY-MM-DD HH:MM:SS", size is $3, key is $4
          split($1, d, /-/); split($2, t, /:/)
          et = mktime(d[1] " " d[2] " " d[3] " " t[1] " " t[2] " " t[3] " 1")
          if ((systime() - et) > max * 86400) print $4
        }' \
    | while read -r obj; do
        echo "[$(date -u +%FT%TZ)] pruning ${obj}"
        $AWS s3 rm "s3://${S3_BUCKET}/${obj}" --only-show-errors || true
      done
}

retention_prune daily 30
retention_prune weekly 90

rm -f "$PG_DUMP" "$QDRANT_SNAP"
echo "[$(date -u +%FT%TZ)] backup complete"