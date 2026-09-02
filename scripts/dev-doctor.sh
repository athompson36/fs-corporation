#!/usr/bin/env bash
# Quick checks for Docker dev on macOS/Linux. Run from the repository root.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT/scripts/run_all_verifications.sh" "$@"
