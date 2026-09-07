#!/usr/bin/env bash
# Path-scoped Tailscale Funnel for GitHub webhooks only.
# Usage (root): bash deploy/fs-dev/tailscale-funnel-webhooks.sh {apply|remove|status}
# Opt-in: FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS=1
set -euo pipefail

CONFIG_DIR="${FS_CORP_CONFIG_DIR:-/etc/fs-corporation}"
ENV_FILE="${FS_CORP_ENV_FILE:-${CONFIG_DIR}/env}"
SECRETS_FILE="${CONFIG_DIR}/secrets.env"
INSTALL_DIR="${FS_CORP_INSTALL_DIR:-/opt/fs-corporation}"
PATH_MOUNT="/api/v1/github/webhooks"
LOCAL_TARGET="http://127.0.0.1:8000/api/v1/github/webhooks"
HTTPS_PORT="${FS_CORP_FUNNEL_HTTPS_PORT:-443}"

die() { echo "tailscale-funnel-webhooks: $*" >&2; exit 1; }
log() { echo "tailscale-funnel-webhooks: $*"; }

require_root() {
  [[ "$(id -u)" -eq 0 ]] || die "must run as root"
}

funnel_enabled_flag() {
  if [[ "${FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS:-}" == "1" ]]; then
    return 0
  fi
  for f in "${ENV_FILE}" "${SECRETS_FILE}"; do
    if [[ -f "${f}" ]] && grep -qE '^FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS=1[[:space:]]*$' "${f}"; then
      return 0
    fi
  done
  return 1
}

require_tailscale() {
  command -v tailscale >/dev/null 2>&1 || die "tailscale CLI not found (run tailscale-join.sh first)"
}

write_env_url() {
  local url="$1"
  mkdir -p "${CONFIG_DIR}"
  if [[ -f "${ENV_FILE}" ]]; then
    if grep -q '^FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL=' "${ENV_FILE}"; then
      sed -i "s|^FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL=.*|FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL=${url}|" "${ENV_FILE}"
    else
      printf '\nFS_CORP_GITHUB_WEBHOOK_PUBLIC_URL=%s\n' "${url}" >> "${ENV_FILE}"
    fi
  else
    printf 'FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL=%s\n' "${url}" > "${ENV_FILE}"
  fi
  chown root:fs-corp "${ENV_FILE}" 2>/dev/null || true
  chmod 640 "${ENV_FILE}" 2>/dev/null || true
}

clear_env_url() {
  [[ -f "${ENV_FILE}" ]] || return 0
  if grep -q '^FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL=' "${ENV_FILE}"; then
    sed -i '/^FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL=/d' "${ENV_FILE}"
  fi
}

resolve_public_url() {
  if [[ -x "${INSTALL_DIR}/.venv/bin/python" ]]; then
    PYTHONPATH="${INSTALL_DIR}" FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS=1 "${INSTALL_DIR}/.venv/bin/python" - <<'PY'
from company.tailscale_funnel import probe_funnel_webhooks
print(probe_funnel_webhooks().get("public_url") or "")
PY
    return 0
  fi
  # Without Python probe, do not invent a MagicDNS URL — Funnel may be disabled.
  return 0
}

cmd_apply() {
  require_root
  require_tailscale
  if ! funnel_enabled_flag; then
    log "FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS!=1 — skip (opt-in)"
    exit 0
  fi
  log "exposing ${PATH_MOUNT} → ${LOCAL_TARGET} (https=${HTTPS_PORT})"
  # Funnel CLI can block indefinitely when the tailnet ACL lacks funnel; fail closed with a timeout.
  local timeout_sec="${FS_CORP_FUNNEL_APPLY_TIMEOUT_SEC:-45}"
  if ! timeout "${timeout_sec}" tailscale funnel --bg --https="${HTTPS_PORT}" --set-path="${PATH_MOUNT}" "${LOCAL_TARGET}"; then
    local rc=$?
    if [[ "${rc}" -eq 124 ]]; then
      die "funnel apply timed out after ${timeout_sec}s — enable Funnel in Tailscale admin (https://login.tailscale.com/admin/acls or node funnel consent URL), then re-run apply"
    fi
    die "funnel apply failed (enable Funnel in Tailscale admin ACL for this node)"
  fi
  local url
  url="$(resolve_public_url || true)"
  if [[ -n "${url}" ]]; then
    write_env_url "${url}"
    log "public webhook URL: ${url}"
  else
    log "WARNING: funnel applied but public URL could not be resolved yet"
  fi
  log "done"
}

cmd_remove() {
  require_root
  require_tailscale
  log "removing funnel path ${PATH_MOUNT}"
  tailscale funnel --https="${HTTPS_PORT}" --set-path="${PATH_MOUNT}" off 2>/dev/null || true
  clear_env_url
  log "done"
}

cmd_status() {
  require_tailscale
  if [[ -x "${INSTALL_DIR}/.venv/bin/python" ]]; then
    if funnel_enabled_flag; then
      export FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS=1
    fi
    if [[ -f "${ENV_FILE}" ]]; then
      # shellcheck disable=SC1090
      set -a
      # Only import the public URL line if present
      eval "$(grep -E '^FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL=' "${ENV_FILE}" || true)"
      set +a
    fi
    PYTHONPATH="${INSTALL_DIR}" "${INSTALL_DIR}/.venv/bin/python" - <<'PY'
import json
from company.tailscale_funnel import probe_funnel_webhooks
print(json.dumps(probe_funnel_webhooks()))
PY
    return 0
  fi
  python3 -c 'import json; print(json.dumps({"opt_in": False, "path": "/api/v1/github/webhooks", "public_url": None, "cli": "live_unavailable"}))'
}

main() {
  local cmd="${1:-status}"
  case "${cmd}" in
    apply) cmd_apply ;;
    remove) cmd_remove ;;
    status) cmd_status ;;
    *) die "usage: $0 {apply|remove|status}" ;;
  esac
}

main "$@"
