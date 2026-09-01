#!/usr/bin/env bash
# Idempotent fs-dev host setup (Debian 12+). Run from the repository root on the target host.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_DIR="${FS_CORP_INSTALL_DIR:-/opt/fs-corporation}"
DATA_DIR="${FS_CORP_DATA_DIR:-/var/lib/fs-corporation}"
CONFIG_DIR="/etc/fs-corporation"
DB_PATH="${FS_CORP_DB:-${DATA_DIR}/company.db}"
TOKEN_FILE="${FS_CORP_TOKEN_FILE:-${CONFIG_DIR}/owner.token}"
COMPANION_DIST="${FS_CORP_COMPANION_DIST:-${DATA_DIR}/companion/dist}"
SERVICE_USER="fs-corp"

log() { printf '==> %s\n' "$*"; }

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "This script must run as root (sudo)." >&2
    exit 1
  fi
}

ensure_user() {
  if ! id -u "${SERVICE_USER}" &>/dev/null; then
    log "Creating system user ${SERVICE_USER}"
    useradd --system --home "${INSTALL_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
  else
    log "User ${SERVICE_USER} already exists"
  fi
}

ensure_packages() {
  log "Installing OS packages (python3.12, venv, build deps, node)"
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3.12 python3.12-venv python3-pip \
    git curl ca-certificates rsync openssl \
    nodejs npm \
    caddy \
    ufw
}

sync_install_tree() {
  log "Syncing application to ${INSTALL_DIR}"
  mkdir -p "${INSTALL_DIR}"
  rsync -a --delete \
    --exclude '.git' --exclude '.venv' --exclude '.local' --exclude 'node_modules' \
    --exclude 'companion/node_modules' --exclude 'companion-native/node_modules' \
    "${REPO_ROOT}/" "${INSTALL_DIR}/"
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}"
}

ensure_venv() {
  log "Python venv and package install"
  if [[ ! -d "${INSTALL_DIR}/.venv" ]]; then
    sudo -u "${SERVICE_USER}" python3.12 -m venv "${INSTALL_DIR}/.venv"
  fi
  sudo -u "${SERVICE_USER}" "${INSTALL_DIR}/.venv/bin/pip" install -U pip wheel
  sudo -u "${SERVICE_USER}" "${INSTALL_DIR}/.venv/bin/pip" install -e "${INSTALL_DIR}"
}

run_migrations() {
  log "Alembic upgrade head (${DB_PATH})"
  mkdir -p "$(dirname "${DB_PATH}")"
  chown "${SERVICE_USER}:${SERVICE_USER}" "$(dirname "${DB_PATH}")"
  local ini_override
  ini_override="$(mktemp)"
  sed "s|^sqlalchemy.url = .*|sqlalchemy.url = sqlite:///${DB_PATH}|" \
    "${INSTALL_DIR}/alembic.ini" > "${ini_override}"
  chown "${SERVICE_USER}:${SERVICE_USER}" "${ini_override}"
  sudo -u "${SERVICE_USER}" "${INSTALL_DIR}/.venv/bin/alembic" -c "${ini_override}" upgrade head
  rm -f "${ini_override}"
}

ensure_dirs() {
  log "Data and config directories"
  mkdir -p "${DATA_DIR}" "${CONFIG_DIR}" "$(dirname "${COMPANION_DIST}")"
  chown "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}"
  chmod 750 "${DATA_DIR}"
  chmod 750 "${CONFIG_DIR}"
  if [[ ! -f "${TOKEN_FILE}" ]]; then
    log "Creating owner token file ${TOKEN_FILE} (store securely; rotate if leaked)"
    install -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 600 /dev/null "${TOKEN_FILE}"
    openssl rand -hex 32 | sudo -u "${SERVICE_USER}" tee "${TOKEN_FILE}" >/dev/null
  else
    chown "${SERVICE_USER}:${SERVICE_USER}" "${TOKEN_FILE}"
    chmod 600 "${TOKEN_FILE}"
  fi
}

build_companion() {
  log "Building companion PWA to ${COMPANION_DIST}"
  pushd "${INSTALL_DIR}/companion" >/dev/null
  if [[ ! -d node_modules ]]; then
    sudo -u "${SERVICE_USER}" npm ci
  else
    sudo -u "${SERVICE_USER}" npm install
  fi
  sudo -u "${SERVICE_USER}" npm run build
  popd >/dev/null
  mkdir -p "${COMPANION_DIST}"
  rsync -a --delete "${INSTALL_DIR}/companion/dist/" "${COMPANION_DIST}/"
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}/companion"
}

install_env_example() {
  if [[ ! -f "${CONFIG_DIR}/env" ]]; then
    log "Installing ${CONFIG_DIR}/env from env.example"
    install -o root -g "${SERVICE_USER}" -m 640 \
      "${INSTALL_DIR}/deploy/fs-dev/env.example" "${CONFIG_DIR}/env"
  else
    log "${CONFIG_DIR}/env already present (not overwritten)"
  fi
}

install_systemd() {
  log "Installing systemd unit"
  install -o root -g root -m 644 \
    "${INSTALL_DIR}/deploy/fs-dev/fs-corporation-api.service" \
    /etc/systemd/system/fs-corporation-api.service
  systemctl daemon-reload
  systemctl enable fs-corporation-api.service
  systemctl restart fs-corporation-api.service
}

print_caddy_instructions() {
  cat <<EOF

Caddy (manual step — edit site addresses first):
  sudo cp ${INSTALL_DIR}/deploy/fs-dev/Caddyfile /etc/caddy/Caddyfile
  # Set LAN IP (and optional Tailscale IP) in the Caddyfile, then:
  sudo systemctl enable --now caddy
  sudo systemctl reload caddy

UFW (review deploy/fs-dev/ufw.rules.example before enabling).

Owner token: ${TOKEN_FILE}
Companion URL: https://\${FS_CORP_LAN_IP:-192.168.4.100}/

EOF
}

main() {
  require_root
  ensure_user
  ensure_packages
  sync_install_tree
  ensure_venv
  ensure_dirs
  run_migrations
  build_companion
  install_env_example
  install_systemd
  print_caddy_instructions
  log "fs-dev install complete"
}

main "$@"
