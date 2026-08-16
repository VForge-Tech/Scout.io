#!/usr/bin/env bash
# Seeds scratch Postgres + Qdrant with a small deterministic dataset.
set -euo pipefail
QDRANT_URL="${QDRANT_URL:-http://qdrant:6333}"
COLLECTION="${QDRANT_COLLECTION:-scout_knowledge}"

echo "== creating collection $COLLECTION =="
curl -sf -X PUT "${QDRANT_URL}/collections/${COLLECTION}" \
  -H 'Content-Type: application/json' \
  -d '{"vectors": {"size": 4, "distance": "Cosine"}}' >/dev/null
echo "collection created"

echo "== upserting points =="
curl -sf -X PUT "${QDRANT_URL}/collections/${COLLECTION}/points?wait=true" \
  -H 'Content-Type: application/json' \
  -d '{
    "points": [
      {"id": 1, "vector": [0.1,0.2,0.3,0.4], "payload": {"text": "how to reset password", "source_id": "doc1"}},
      {"id": 2, "vector": [0.4,0.3,0.2,0.1], "payload": {"text": "billing and invoices", "source_id": "doc2"}},
      {"id": 3, "vector": [0.5,0.1,0.5,0.1], "payload": {"text": "api rate limits", "source_id": "doc3"}}
    ]
  }' >/dev/null
echo "points upserted"

COUNT="$(curl -sf "${QDRANT_URL}/collections/${COLLECTION}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["points_count"])')"
echo "points_count: $COUNT"
test "$COUNT" = "3"