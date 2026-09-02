#!/usr/bin/env bash
# Quick checks for Docker dev on macOS/Linux. Run from the repository root.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Repository: $ROOT"
if [[ -d "$ROOT/fs-corporation/.git" ]]; then
  echo "WARN: Nested clone at $ROOT/fs-corporation — remove it and use this directory only:"
  echo "      rm -rf $ROOT/fs-corporation"
fi
if [[ ! -f .env ]]; then
  echo "ERROR: .env missing. Copy deploy/fs-dev/secrets.example.env ideas into .env (gitignored)."
  exit 1
fi
echo "==> .env present"
echo "==> Git: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

if ! docker compose ps --status running 2>/dev/null | grep -q api; then
  echo "==> Starting API container..."
  docker compose up -d --build
fi

echo "==> Container checks"
docker compose exec -T api python -c "import company; print('package version', company.__version__)"
docker compose exec -T api test -f /src/scripts/verify_model_provider.py \
  || { echo "ERROR: scripts not mounted — run from repo root and: docker compose up -d --force-recreate"; exit 1; }

echo "==> Model provider"
docker compose exec -T api python scripts/verify_model_provider.py

echo "==> Done. API: http://localhost:8013"
