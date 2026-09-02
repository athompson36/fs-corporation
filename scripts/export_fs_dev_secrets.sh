#!/usr/bin/env bash
# Emit fs-dev secrets.env lines from local .env (for owner copy to Debian host).
# Does not print secret values — only whether each key is set and suggested fs-dev paths.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$ROOT/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "No .env at $ENV_FILE" >&2
  exit 1
fi

has_key() {
  grep -q "^${1}=" "$ENV_FILE" 2>/dev/null && [[ -n "$(grep "^${1}=" "$ENV_FILE" | cut -d= -f2- | tr -d '[:space:]')" ]]
}

cat <<'EOF'
# Paste into /etc/fs-corporation/secrets.env on the fs-dev host (chmod 600).
# Copy PEM files to /etc/fs-corporation/ and paste API key values from your local .env.

EOF

if has_key GITHUB_APP_ID; then echo "GITHUB_APP_ID=$(grep '^GITHUB_APP_ID=' "$ENV_FILE" | cut -d= -f2-)"; fi
if has_key GITHUB_INSTALLATION_ID; then echo "GITHUB_INSTALLATION_ID=$(grep '^GITHUB_INSTALLATION_ID=' "$ENV_FILE" | cut -d= -f2-)"; fi
if [[ -f "$ROOT/secrets/github-app.pem" ]]; then
  echo "GITHUB_PRIVATE_KEY_FILE=/etc/fs-corporation/github-app.pem"
  echo "# scp $ROOT/secrets/github-app.pem root@192.168.4.100:/etc/fs-corporation/github-app.pem"
fi
if has_key MODEL_PROVIDER_API_KEY; then echo "MODEL_PROVIDER_API_KEY=$(grep '^MODEL_PROVIDER_API_KEY=' "$ENV_FILE" | cut -d= -f2-)"; fi
if has_key ANTHROPIC_API_KEY; then echo "ANTHROPIC_API_KEY=$(grep '^ANTHROPIC_API_KEY=' "$ENV_FILE" | cut -d= -f2-)"; fi
if [[ -f "$ROOT/secrets/vapid-private.pem" ]]; then
  echo "VAPID_PUBLIC_KEY_FILE=/etc/fs-corporation/vapid-public.pem"
  echo "VAPID_PRIVATE_KEY_FILE=/etc/fs-corporation/vapid-private.pem"
  if has_key VAPID_CONTACT_EMAIL; then
    echo "VAPID_CONTACT_EMAIL=$(grep '^VAPID_CONTACT_EMAIL=' "$ENV_FILE" | cut -d= -f2-)"
  else
    echo "VAPID_CONTACT_EMAIL=mailto:owner@example.com"
  fi
  echo "# scp $ROOT/secrets/vapid-*.pem root@192.168.4.100:/etc/fs-corporation/"
fi

echo ""
echo "# Then: sudo systemctl restart fs-corporation-api"
