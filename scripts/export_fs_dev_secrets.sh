#!/usr/bin/env bash
# Emit fs-dev secrets.env lines from local .env (for owner copy to Debian host).
# Does not print secret values — only whether each key is set and suggested fs-dev paths.
# Values are emitted as PASTE_FROM_LOCAL_ENV placeholders; fill them in on the host.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$ROOT/.env}"
PLACEHOLDER="PASTE_FROM_LOCAL_ENV"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "No .env at $ENV_FILE" >&2
  exit 1
fi

has_key() {
  grep -q "^${1}=" "$ENV_FILE" 2>/dev/null && [[ -n "$(grep "^${1}=" "$ENV_FILE" | cut -d= -f2- | tr -d '[:space:]')" ]]
}

# Emit "KEY=<placeholder>" when set locally; report status on stderr either way.
emit_key() {
  local key="$1"
  if has_key "$key"; then
    echo "${key}=${PLACEHOLDER}"
    echo "  set locally:     ${key}" >&2
  else
    echo "# ${key}= (not set in ${ENV_FILE})"
    echo "  NOT set locally: ${key}" >&2
  fi
}

echo "Key status from ${ENV_FILE} (values never printed):" >&2

cat <<EOF
# Paste into /etc/fs-corporation/secrets.env on the fs-dev host (chmod 600).
# Copy PEM files to /etc/fs-corporation/ and replace each ${PLACEHOLDER} with the
# matching value from your local .env. Never commit this file.

EOF

emit_key GITHUB_APP_ID
emit_key GITHUB_INSTALLATION_ID
if [[ -f "$ROOT/secrets/github-app.pem" ]]; then
  echo "GITHUB_PRIVATE_KEY_FILE=/etc/fs-corporation/github-app.pem"
  echo "# scp $ROOT/secrets/github-app.pem root@192.168.4.100:/etc/fs-corporation/github-app.pem"
fi
emit_key GITHUB_WEBHOOK_SECRET
emit_key MODEL_PROVIDER_API_KEY
emit_key ANTHROPIC_API_KEY
if [[ -f "$ROOT/secrets/vapid-private.pem" ]]; then
  echo "VAPID_PUBLIC_KEY_FILE=/etc/fs-corporation/vapid-public.pem"
  echo "VAPID_PRIVATE_KEY_FILE=/etc/fs-corporation/vapid-private.pem"
  if has_key VAPID_CONTACT_EMAIL; then
    emit_key VAPID_CONTACT_EMAIL
  else
    echo "VAPID_CONTACT_EMAIL=mailto:owner@example.com"
  fi
  echo "# scp $ROOT/secrets/vapid-*.pem root@192.168.4.100:/etc/fs-corporation/"
fi

echo ""
echo "# Then: sudo systemctl restart fs-corporation-api"
