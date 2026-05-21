#!/usr/bin/env bash
# Verify Aethera memory (Vectorize) end-to-end against the deployed Worker.
#
#   WORKER_URL=https://<your-worker-url> API_KEY=<one of API_KEYS> \
#     bash worker/scripts/verify-memory.sh
#
# Stores a memory, then searches for it semantically. Passes if the stored
# note comes back in the search results.
set -euo pipefail

WORKER_URL="${WORKER_URL:-${1:-}}"
API_KEY="${API_KEY:-${2:-}}"

if [[ -z "$WORKER_URL" || -z "$API_KEY" ]]; then
  echo "Usage: WORKER_URL=https://<worker> API_KEY=<key> bash worker/scripts/verify-memory.sh"
  echo "   or: bash worker/scripts/verify-memory.sh <worker-url> <api-key>"
  exit 2
fi
WORKER_URL="${WORKER_URL%/}"  # strip trailing slash

NOTE="ACME Clinic prefers afternoon appointments and appeals all CO-50 denials"
AUTH="Authorization: Bearer ${API_KEY}"
JSON="Content-Type: application/json"

echo "==> 1/3 health"
curl -sS -H "$AUTH" "${WORKER_URL}/api/health"; echo

echo "==> 2/3 store a memory"
STORE=$(curl -sS -H "$AUTH" -H "$JSON" -X POST "${WORKER_URL}/api/memory" \
  -d "{\"text\":\"${NOTE}\",\"metadata\":{\"user_id\":\"default_user\"}}")
echo "$STORE"
case "$STORE" in
  *'"stored":true'*) echo "    OK: memory stored" ;;
  *) echo "    FAIL: not stored — is the [[vectorize]] binding uncommented and redeployed?"; exit 1 ;;
esac

echo "==> waiting 2s for the index to update"; sleep 2

echo "==> 3/3 semantic search"
SEARCH=$(curl -sS -H "$AUTH" -H "$JSON" -X POST "${WORKER_URL}/api/memory/search" \
  -d '{"query":"when does ACME like appointments?","user_id":"default_user"}')
echo "$SEARCH"
case "$SEARCH" in
  *afternoon*|*ACME*) echo "    PASS: memory recalled end-to-end ✅" ;;
  *) echo "    WARN: no matching recall. Check index dimensions (must be 768) and that vectors finished indexing (retry in a few seconds)."; exit 1 ;;
esac
