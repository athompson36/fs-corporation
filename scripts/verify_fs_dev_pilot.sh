#!/usr/bin/env bash
# Live pilot checks on fs-dev (run on the host or via ssh with owner token).
# Does not print secrets. Exit 0 when GitHub, model, workers, and container dispatch succeed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${FS_CORP_API_BASE:-http://127.0.0.1:8000}"
DB="${FS_CORP_DB:-/Data/fs-corporation/data/company.db}"
TOKEN_FILE="${FS_CORP_TOKEN_FILE:-}"
PY="${FS_CORP_PYTHON:-/opt/fs-corporation/.venv/bin/python}"
SCRIPTS="${FS_CORP_SCRIPTS:-/opt/fs-corporation/scripts}"

if [[ -z "${TOKEN_FILE}" ]]; then
  for candidate in /tmp/owner.token.exercise "$HOME/Desktop/fs-corp-owner.token" /etc/fs-corporation/owner.token; do
    if [[ -r "${candidate}" ]]; then
      TOKEN_FILE="${candidate}"
      break
    fi
  done
fi
[[ -n "${TOKEN_FILE}" && -r "${TOKEN_FILE}" ]] || {
  echo "Set FS_CORP_TOKEN_FILE to a readable owner token path." >&2
  exit 1
}

TOKEN="$(<"${TOKEN_FILE}")"
auth=(-H "Authorization: Bearer ${TOKEN}")

step() { printf '\n==> %s\n' "$*"; }

step "API health"
curl -fsS "${BASE}/api/v1/health" | grep -q '"ok":true'

step "GitHub status"
gh="$(curl -fsS "${auth[@]}" "${BASE}/api/v1/github/status")"
echo "${gh}" | grep -q '"live":true' || { echo "${gh}" >&2; exit 1; }

step "Model status"
md="$(curl -fsS "${auth[@]}" "${BASE}/api/v1/model/status")"
echo "${md}" | grep -q '"live":true' || { echo "${md}" >&2; exit 1; }

step "Workers status"
curl -fsS "${auth[@]}" "${BASE}/api/v1/workers/status" | grep -q '"container_dispatch_ready":true'

step "Container dispatch"
TASK_ID="container-pilot-$(date +%s)"
"${PY}" "${SCRIPTS}/exercise_container_dispatch.py" \
  --base "${BASE}" \
  --token-file "${TOKEN_FILE}" \
  --db "${DB}" \
  --task-id "${TASK_ID}"

step "Remote access (Tailscale)"
curl -fsS "${auth[@]}" "${BASE}/api/v1/remote-access" | grep -q '"auth_key_configured":true'

echo ""
echo "fs-dev live pilot OK (GitHub + model + container worker + Tailscale pairing)."
