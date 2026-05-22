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

# If the Worker hostname is behind Cloudflare Access, pass a service token so
# machine-to-machine calls get through (set both env vars).
ACCESS=()
if [[ -n "${CF_ACCESS_CLIENT_ID:-}" && -n "${CF_ACCESS_CLIENT_SECRET:-}" ]]; then
  ACCESS=(-H "CF-Access-Client-Id: ${CF_ACCESS_CLIENT_ID}" -H "CF-Access-Client-Secret: ${CF_ACCESS_CLIENT_SECRET}")
fi

access_check() {
  case "$1" in
    *"302 Found"*|*cloudflareaccess*)
      echo "    NOTE: blocked by Cloudflare Access (login redirect). Provide a service token:"
      echo "          CF_ACCESS_CLIENT_ID=... CF_ACCESS_CLIENT_SECRET=... (see worker/DEPLOY notes)"
      ;;
  esac
}

echo "==> 1/3 health"
H=$(curl -sS "${ACCESS[@]}" -H "$AUTH" "${WORKER_URL}/api/health"); echo "$H"; access_check "$H"

echo "==> 2/3 store a memory"
STORE=$(curl -sS "${ACCESS[@]}" -H "$AUTH" -H "$JSON" -X POST "${WORKER_URL}/api/memory" \
  -d "{\"text\":\"${NOTE}\",\"metadata\":{\"user_id\":\"default_user\"}}")
echo "$STORE"; access_check "$STORE"
case "$STORE" in
  *'"stored":true'*) echo "    OK: memory stored" ;;
  *) echo "    FAIL: not stored — check the [[vectorize]] binding (redeploy) or Cloudflare Access above."; exit 1 ;;
esac

echo "==> waiting 2s for the index to update"; sleep 2

echo "==> 3/3 semantic search"
SEARCH=$(curl -sS "${ACCESS[@]}" -H "$AUTH" -H "$JSON" -X POST "${WORKER_URL}/api/memory/search" \
  -d '{"query":"when does ACME like appointments?","user_id":"default_user"}')
echo "$SEARCH"
case "$SEARCH" in
  *afternoon*|*ACME*) echo "    PASS: memory recalled end-to-end ✅" ;;
  *) echo "    WARN: no matching recall. Check index dimensions (must be 768) and that vectors finished indexing (retry in a few seconds)."; exit 1 ;;
esac
