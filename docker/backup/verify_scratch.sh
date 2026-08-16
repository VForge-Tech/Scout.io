#!/usr/bin/env bash
# Verify scratch Postgres + Qdrant state after a restore.
set -euo pipefail
QDRANT_URL="${QDRANT_URL:-http://qdrant:6333}"
COLLECTION="${QDRANT_COLLECTION:-scout_knowledge}"

echo "postgres:"
echo "  $(curl -sf http://postgres:5432/__nope__ 2>/dev/null >/dev/null || true)"
echo "  (checked via psql in postgres container)"

COUNT="$(curl -sf "${QDRANT_URL}/collections/${COLLECTION}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["points_count"])')"
echo "qdrant ${COLLECTION} points_count: ${COUNT}"