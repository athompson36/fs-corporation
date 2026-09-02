#!/usr/bin/env bash
# Run all Docker dev integration checks. Exit non-zero on first failure.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
FAIL=0

step() { printf '\n==> %s\n' "$*"; }
run() {
  if "$@"; then
    echo "OK: $*"
  else
    echo "FAIL: $*" >&2
    FAIL=1
  fi
}

step "Repository: $ROOT ($(git rev-parse --short HEAD 2>/dev/null || echo unknown))"
if [[ -d "$ROOT/fs-corporation/.git" ]]; then
  echo "ERROR: Nested clone at $ROOT/fs-corporation — run: rm -rf $ROOT/fs-corporation" >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  echo "ERROR: .env missing at $ROOT/.env" >&2
  exit 1
fi

step "Docker API container"
if ! docker compose ps --status running 2>/dev/null | grep -q api; then
  docker compose up -d --build --force-recreate
fi
run docker compose exec -T api test -f /src/scripts/verify_model_provider.py

step "Owner config (host .env)"
run python3 scripts/check_owner_config.py

step "Verify integrations (in container)"
run docker compose exec -T api python scripts/verify_model_provider.py
run docker compose exec -T api python scripts/verify_github_app.py
run docker compose exec -T api python scripts/verify_vapid.py
run docker compose exec -T api python scripts/verify_push_delivery.py
run docker compose exec -T api python scripts/verify_fs_dev_workers.py

step "Live model smoke (OpenAI + Anthropic)"
run docker compose exec -T api python -c "
import os
from company.core import Company
c = Company(os.environ['FS_CORP_DB'])
o = c.invoke_model('pilot', 'Reply with exactly: openai pilot OK', {'profiles': {
  'pilot': {'provider': 'openai', 'model': 'gpt-4o-mini', 'enabled': True,
            'capabilities': ['text'], 'allowed_data': ['public']}}})
assert 'openai pilot OK' in o['text'], o
a = c.invoke_model('pilot', 'Reply with exactly: claude pilot OK', {'profiles': {
  'pilot': {'provider': 'anthropic', 'model': 'claude-sonnet-5', 'enabled': True,
            'capabilities': ['text'], 'allowed_data': ['public'],
            'credential_ref': 'ANTHROPIC_API_KEY'}}})
assert 'claude pilot OK' in a['text'], a
c.close()
print('both models OK')
"

step "Market feed poll"
TOKEN_FILE="$(mktemp)"
docker compose exec -T api cat /data/owner.token > "$TOKEN_FILE"
run python3 scripts/exercise_feed_poll.py \
  --token-file "$TOKEN_FILE" \
  --feed-id "github-blog-$(date +%s)"
rm -f "$TOKEN_FILE"

step "Container worker dispatch"
TOKEN_FILE="$(mktemp)"
docker compose exec -T api cat /data/owner.token > "$TOKEN_FILE"
run python3 scripts/exercise_container_dispatch.py \
  --token-file "$TOKEN_FILE" \
  --task-id "container-pilot-$(date +%s)"
rm -f "$TOKEN_FILE"

step "Unit tests"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  run "$ROOT/.venv/bin/python" -m unittest discover -s tests -q
else
  run docker compose exec -T api python -m unittest discover -s tests -q
fi

step "Bundle check"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  run "$ROOT/.venv/bin/python" scripts/check_bundle.py
else
  run python3 scripts/check_bundle.py
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "One or more checks failed." >&2
  exit 1
fi
echo ""
echo "All checks passed. API: http://localhost:8013"
