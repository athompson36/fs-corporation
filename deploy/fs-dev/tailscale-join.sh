#!/usr/bin/env bash
# Install Tailscale on fs-dev and join with FS_CORP_TAILSCALE_AUTHKEY.
# Usage (root): FS_CORP_TAILSCALE_AUTHKEY=… bash deploy/fs-dev/tailscale-join.sh
# Does not print the auth key.
set -euo pipefail

CONFIG_DIR="${FS_CORP_CONFIG_DIR:-/etc/fs-corporation}"
ENV_FILE="${FS_CORP_ENV_FILE:-${CONFIG_DIR}/env}"
HOSTNAME_TS="${FS_CORP_TAILSCALE_HOSTNAME:-fs-dev}"

die() { echo "tailscale-join: $*" >&2; exit 1; }

require_root() {
  [[ "$(id -u)" -eq 0 ]] || die "must run as root"
}

load_auth_key() {
  if [[ -n "${FS_CORP_TAILSCALE_AUTHKEY:-}" ]]; then
    return 0
  fi
  local secrets="${CONFIG_DIR}/secrets.env"
  if [[ -f "${secrets}" ]]; then
    # shellcheck disable=SC1090
    FS_CORP_TAILSCALE_AUTHKEY="$(grep -E '^FS_CORP_TAILSCALE_AUTHKEY=' "${secrets}" | tail -n1 | cut -d= -f2- || true)"
    export FS_CORP_TAILSCALE_AUTHKEY
  fi
  [[ -n "${FS_CORP_TAILSCALE_AUTHKEY:-}" ]] || die "FS_CORP_TAILSCALE_AUTHKEY not set (env or secrets.env)"
}

ensure_tailscale_pkg() {
  if command -v tailscale >/dev/null 2>&1; then
    return 0
  fi
  echo "tailscale-join: installing Tailscale package"
  curl -fsSL https://tailscale.com/install.sh | sh
}

join_tailnet() {
  systemctl enable --now tailscaled
  # Idempotent: already logged in is ok
  if tailscale status --json 2>/dev/null | grep -q '"BackendState": "Running"'; then
    echo "tailscale-join: already running"
  else
    echo "tailscale-join: bringing up node hostname=${HOSTNAME_TS}"
    tailscale up --auth-key="${FS_CORP_TAILSCALE_AUTHKEY}" --hostname="${HOSTNAME_TS}" --accept-routes=false
  fi
}

write_tailscale_ip() {
  local ip
  ip="$(tailscale ip -4 | head -n1 | tr -d '[:space:]')"
  [[ -n "${ip}" ]] || die "could not read tailscale ipv4"
  mkdir -p "${CONFIG_DIR}"
  if [[ -f "${ENV_FILE}" ]]; then
    if grep -q '^FS_CORP_TAILSCALE_IP=' "${ENV_FILE}"; then
      sed -i "s|^FS_CORP_TAILSCALE_IP=.*|FS_CORP_TAILSCALE_IP=${ip}|" "${ENV_FILE}"
    else
      printf '\nFS_CORP_TAILSCALE_IP=%s\n' "${ip}" >> "${ENV_FILE}"
    fi
  else
    printf 'FS_CORP_TAILSCALE_IP=%s\n' "${ip}" > "${ENV_FILE}"
  fi
  chown root:fs-corp "${ENV_FILE}" 2>/dev/null || true
  chmod 640 "${ENV_FILE}" 2>/dev/null || true
  echo "tailscale-join: FS_CORP_TAILSCALE_IP=${ip}"
}

patch_caddy() {
  local ip caddy=/etc/caddy/Caddyfile
  ip="$(tailscale ip -4 | head -n1 | tr -d '[:space:]')"
  [[ -f "${caddy}" ]] || { echo "tailscale-join: no ${caddy}; skip Caddy patch"; return 0; }
  if grep -q '# fs-corp-tailscale-site' "${caddy}"; then
    sed -i '/# fs-corp-tailscale-site/,/# fs-corp-tailscale-site-end/d' "${caddy}"
  fi
  cat >> "${caddy}" <<EOF

# fs-corp-tailscale-site
https://${ip} {
	import lan_site
}
http://${ip} {
	import lan_site
}
# fs-corp-tailscale-site-end
EOF
  echo "tailscale-join: Caddy sites https://${ip} and http://${ip}"
  caddy validate --config "${caddy}" --adapter caddyfile
  systemctl restart caddy
}

main() {
  require_root
  load_auth_key
  ensure_tailscale_pkg
  join_tailnet
  write_tailscale_ip
  patch_caddy
  echo "tailscale-join: done"
}

main "$@"
