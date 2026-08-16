#!/usr/bin/env bash
# Scout.io disaster-recovery restore wrapper.
#
# Runs the backup container's restore.sh against the host Docker daemon, so the
# script needs only: a running Docker, the backup image, and object-store creds.
#
# Usage (from repo root):
#   scripts/restore.sh --timestamp 20260815T030000Z [--project scout] [--latest]
#
# The restore itself (docker/backup/restore.sh) runs inside the container with
# the host docker.sock mounted so it can drive docker compose.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${PROJECT:-scout}"

# Which compose file(s) to rebuild. Default: the production stack is the base
# compose layered with the prod overlay, so pass both (-f list, space separated).
# Override for scratch/DR tests:  COMPOSE_FILE="docker/docker-compose.scratch.yml"
COMPOSE_REL="${COMPOSE_FILE:-docker/docker-compose.yml docker/docker-compose.prod.yml}"

# Build the backup image if not present.
if ! docker image inspect scout-backup >/dev/null 2>&1; then
  echo "[restore] building backup image..."
  docker build -t scout-backup "${ROOT}/docker/backup"
fi

# Object-store creds must be present in the environment (or docker/.env).
if [ -z "${S3_ENDPOINT:-}" ] && [ -f "${ROOT}/docker/.env" ]; then
  set -a; source "${ROOT}/docker/.env"; set +a
fi

: "${S3_ENDPOINT:?S3_ENDPOINT required (see docker/.env or docs/disaster-recovery.md)}"
: "${S3_BUCKET:?S3_BUCKET required}"

# The backup container needs to be on the compose network to reach postgres/qdrant.
NET="$(docker network ls --format '{{.Name}}' | grep -E "^${PROJECT}_default$" | head -1 || true)"
NET_ARGS=()
if [ -n "$NET" ]; then
  NET_ARGS=(--network "$NET")
fi

# Prefix each compose file with the in-container /app mount.
IN_FILES=""
for f in $COMPOSE_REL; do
  IN_FILES="${IN_FILES:+$IN_FILES }/app/${f}"
done

exec docker run --rm "${NET_ARGS[@]}" \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v "${ROOT}":/app:ro \
  -e S3_ENDPOINT -e S3_BUCKET -e S3_ACCESS_KEY -e S3_SECRET_KEY -e S3_REGION \
  -e S3_PREFIX -e COMPOSE_FILE="$IN_FILES" -e PROJECT="$PROJECT" \
  -e POSTGRES_HOST -e POSTGRES_PORT -e POSTGRES_USER -e POSTGRES_PASSWORD -e POSTGRES_DB \
  -e QDRANT_URL -e QDRANT_COLLECTION \
  scout-backup /scripts/restore.sh --compose-file "$IN_FILES" "$@"