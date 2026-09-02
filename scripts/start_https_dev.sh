#!/usr/bin/env bash
# Build companion and start Docker dev with HTTPS same-origin (Web Push secure context).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "==> Building companion PWA"
(cd companion && npm run build)
echo "==> Starting API + Caddy on https://localhost:8443"
export FS_CORP_PUBLIC_URL="${FS_CORP_PUBLIC_URL:-https://localhost:8443}"
docker compose --profile https up -d --build
echo ""
echo "Open https://localhost:8443 and paste owner token from:"
echo "  docker compose exec api cat /data/owner.token"
echo "Then Settings → allow notifications → Send test push"
echo "Or: python3 scripts/exercise_push_notify.py --token-file <(docker compose exec -T api cat /data/owner.token)"
