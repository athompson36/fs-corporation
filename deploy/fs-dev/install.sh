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

require_linux() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    cat >&2 <<'EOF'
fs-dev install.sh is for Debian/Ubuntu production hosts only.

On macOS or Windows, use Docker dev instead:
  cd /path/to/fs-corporation
  docker compose up --build -d
  docker compose exec api cat /data/owner.token

See deploy/dev/README.md — not deploy/fs-dev/install.sh.
EOF
    exit 1
  fi
}

ensure_user() {
  if ! id -u "${SERVICE_USER}" &>/dev/null; then
    log "Creating system user ${SERVICE_USER}"
    useradd --system --home "${INSTALL_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
  else
    log "User ${SERVICE_USER} already exists"
    # Keep home on the app install dir (ext4). NTFS homes break npm rename/cache.
    usermod -d "${INSTALL_DIR}" "${SERVICE_USER}" 2>/dev/null || true
  fi
}

ensure_packages() {
  log "Installing OS packages (python3.12, venv, build deps, node, docker)"
  repair_apt_sources
  if ! apt-get update -qq; then
    log "WARNING: apt-get update reported errors; will install from available indexes"
  fi
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3.12 python3.12-venv python3-pip \
    git curl ca-certificates rsync openssl \
    nodejs npm \
    caddy \
    ufw \
    docker.io || {
      log "WARNING: apt-get install incomplete — checking required tools"
      command -v python3.12 >/dev/null
      command -v docker >/dev/null
      command -v node >/dev/null || command -v nodejs >/dev/null
    }
}

repair_apt_sources() {
  # docker.sources sometimes stores unexpanded shell for Suites (breaks apt update)
  local ds=/etc/apt/sources.list.d/docker.sources
  if [[ -f "${ds}" ]] && grep -q '\$(' "${ds}"; then
    local codename
    # shellcheck disable=SC1091
    codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")"
    log "Repairing ${ds} Suites → ${codename}"
    sed -i "s|^Suites:.*|Suites: ${codename}|" "${ds}"
  fi
  # Prefer one Docker apt source; both .list and .sources cause confusion
  if [[ -f /etc/apt/sources.list.d/docker.sources && -f /etc/apt/sources.list.d/docker.list ]]; then
    log "Disabling duplicate docker.list (keeping docker.sources)"
    mv -f /etc/apt/sources.list.d/docker.list /etc/apt/sources.list.d/docker.list.disabled
  fi
  # Empty GitHub CLI keyring breaks apt update
  local gh_list=/etc/apt/sources.list.d/github-cli.list
  local gh_key=/usr/share/keyrings/githubcli-archive-keyring.gpg
  if [[ -f "${gh_list}" ]] && [[ ! -s "${gh_key}" ]]; then
    log "Disabling github-cli.list (empty keyring at ${gh_key})"
    mv -f "${gh_list}" "${gh_list}.disabled"
  fi
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
  # Prefer creating the venv as root then chown — service users often cannot
  # ensurepip on NTFS/fuse data volumes (nosuid / permission translation).
  if [[ -d "${INSTALL_DIR}/.venv" ]] && ! "${INSTALL_DIR}/.venv/bin/python" -c "import pip" 2>/dev/null; then
    log "Removing incomplete venv"
    rm -rf "${INSTALL_DIR}/.venv"
  fi
  if [[ ! -d "${INSTALL_DIR}/.venv" ]]; then
    if ! python3.12 -m venv "${INSTALL_DIR}/.venv"; then
      log "venv with ensurepip failed; retrying --without-pip + get-pip"
      rm -rf "${INSTALL_DIR}/.venv"
      python3.12 -m venv --without-pip "${INSTALL_DIR}/.venv"
      curl -fsSL https://bootstrap.pypa.io/get-pip.py | "${INSTALL_DIR}/.venv/bin/python"
    fi
  fi
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}"
  sudo -u "${SERVICE_USER}" "${INSTALL_DIR}/.venv/bin/pip" install -U pip wheel
  sudo -u "${SERVICE_USER}" "${INSTALL_DIR}/.venv/bin/pip" install -e "${INSTALL_DIR}"
}

run_migrations() {
  log "Alembic upgrade head (${DB_PATH})"
  mkdir -p "$(dirname "${DB_PATH}")"
  chown "${SERVICE_USER}:${SERVICE_USER}" "$(dirname "${DB_PATH}")"
  local ini_override
  ini_override="$(mktemp)"
  # Absolute script_location: alembic resolves a relative path from CWD, and
  # run-install.sh may cd into a mode-700 home deploy tree that fs-corp cannot read.
  sed \
    -e "s|^sqlalchemy.url = .*|sqlalchemy.url = sqlite:///${DB_PATH}|" \
    -e "s|^script_location = .*|script_location = ${INSTALL_DIR}/alembic|" \
    "${INSTALL_DIR}/alembic.ini" > "${ini_override}"
  chown "${SERVICE_USER}:${SERVICE_USER}" "${ini_override}"
  sudo -u "${SERVICE_USER}" "${INSTALL_DIR}/.venv/bin/alembic" -c "${ini_override}" upgrade head
  rm -f "${ini_override}"
}

ensure_dirs() {
  log "Data and config directories"
  mkdir -p "${DATA_DIR}" "${CONFIG_DIR}" "$(dirname "${COMPANION_DIST}")" "${DATA_DIR}/worker-scratch"
  chown "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}" 2>/dev/null || true
  chmod 750 "${DATA_DIR}" 2>/dev/null || true
  chmod 750 "${DATA_DIR}/worker-scratch" 2>/dev/null || true
  # Config stays root:fs-corp so the service can read; token is written as root.
  chown root:"${SERVICE_USER}" "${CONFIG_DIR}"
  chmod 750 "${CONFIG_DIR}"
  if [[ ! -s "${TOKEN_FILE}" ]]; then
    log "Creating owner token file ${TOKEN_FILE} (store securely; rotate if leaked)"
    umask 077
    openssl rand -hex 32 > "${TOKEN_FILE}"
    chown "${SERVICE_USER}:${SERVICE_USER}" "${TOKEN_FILE}"
    chmod 600 "${TOKEN_FILE}"
  else
    chown "${SERVICE_USER}:${SERVICE_USER}" "${TOKEN_FILE}"
    chmod 600 "${TOKEN_FILE}"
  fi
}

build_companion() {
  log "Building companion PWA to ${COMPANION_DIST}"
  local npm_cache="${INSTALL_DIR}/.npm-cache"
  mkdir -p "${npm_cache}"
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}/companion" "${npm_cache}"
  pushd "${INSTALL_DIR}/companion" >/dev/null
  # An interrupted earlier install can leave packages half-extracted (missing .mjs/.d.ts).
  # npm install will not repair those, so always start from a clean tree.
  rm -rf node_modules
  # Force npm cache onto the install filesystem (ext4). A home on NTFS/fuse breaks cacache rename.
  local npm_env=(env HOME="${INSTALL_DIR}" npm_config_cache="${npm_cache}" npm_config_audit=false npm_config_fund=false)
  if [[ -f package-lock.json ]]; then
    sudo -u "${SERVICE_USER}" "${npm_env[@]}" npm ci
  else
    sudo -u "${SERVICE_USER}" "${npm_env[@]}" npm install
  fi
  if [[ ! -f node_modules/workbox-precaching/index.mjs ]]; then
    log "npm tree still incomplete; clearing cache ${npm_cache} and retrying"
    rm -rf node_modules "${npm_cache}"
    mkdir -p "${npm_cache}"
    chown "${SERVICE_USER}:${SERVICE_USER}" "${npm_cache}"
    sudo -u "${SERVICE_USER}" "${npm_env[@]}" npm install
  fi
  sudo -u "${SERVICE_USER}" "${npm_env[@]}" npm run build
  popd >/dev/null
  mkdir -p "${COMPANION_DIST}"
  rsync -a --delete "${INSTALL_DIR}/companion/dist/" "${COMPANION_DIST}/"
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}/companion" 2>/dev/null || true
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

configure_gateway_egress() {
  local env_file="${CONFIG_DIR}/env"
  local mode="default"
  local nic_ip="${FS_CORP_WORKER_NIC_IP:-}"
  if [[ -f "${env_file}" ]]; then
    local line
    line=$(grep -E '^FS_CORP_GATEWAY_EGRESS=' "${env_file}" | tail -n1 || true)
    if [[ -n "${line}" ]]; then
      mode="${line#FS_CORP_GATEWAY_EGRESS=}"
    fi
    line=$(grep -E '^FS_CORP_WORKER_NIC_IP=' "${env_file}" | tail -n1 || true)
    if [[ -n "${line}" ]]; then
      nic_ip="${line#FS_CORP_WORKER_NIC_IP=}"
    fi
  fi
  mode="${mode:-default}"
  export FS_CORP_GATEWAY_EGRESS="${mode}"
  export FS_CORP_WORKER_NIC_IP="${nic_ip}"
  export FS_CORP_SERVICE_USER="${SERVICE_USER}"
  local script="${INSTALL_DIR}/deploy/fs-dev/gateway-egress.sh"
  chmod +x "${script}"
  if [[ "${mode}" == "worker_nic" ]]; then
    log "Applying gateway egress via worker NIC (${nic_ip})"
    bash "${script}" apply
  else
    log "Gateway egress mode=${mode}; clearing policy routing if present"
    bash "${script}" remove
  fi
  bash "${script}" status || true
}

ensure_docker_access() {
  log "Docker group access for ${SERVICE_USER}"
  groupadd -f docker
  usermod -aG docker "${SERVICE_USER}"
  systemctl enable --now docker
}

build_worker_image() {
  if [[ "${FS_CORP_SKIP_WORKER_BUILD:-0}" == "1" ]]; then
    log "Skipping worker image build (FS_CORP_SKIP_WORKER_BUILD=1)"
    return
  fi
  log "Building container worker image fs-corporation-worker:local"
  docker build -f "${INSTALL_DIR}/deploy/fs-dev/Dockerfile.worker" \
    -t fs-corporation-worker:local "${INSTALL_DIR}"
}

bootstrap_company() {
  log "Bootstrap default policy grants and project app (idempotent)"
  sudo -u "${SERVICE_USER}" FS_CORP_DB="${DB_PATH}" \
    "${INSTALL_DIR}/.venv/bin/python" "${INSTALL_DIR}/scripts/bootstrap_dev_company.py"
}

install_systemd() {
  log "Installing systemd unit (paths: install=${INSTALL_DIR} data=${DATA_DIR})"
  local unit=/etc/systemd/system/fs-corporation-api.service
  sed \
    -e "s|__INSTALL_DIR__|${INSTALL_DIR}|g" \
    -e "s|__DATA_DIR__|${DATA_DIR}|g" \
    -e "s|__DB_PATH__|${DB_PATH}|g" \
    -e "s|__TOKEN_FILE__|${TOKEN_FILE}|g" \
    "${INSTALL_DIR}/deploy/fs-dev/fs-corporation-api.service" > "${unit}.tmp"
  install -o root -g root -m 644 "${unit}.tmp" "${unit}"
  rm -f "${unit}.tmp"
  systemctl daemon-reload
  systemctl enable fs-corporation-api.service
  systemctl restart fs-corporation-api.service
}

install_caddy_site() {
  if [[ "${FS_CORP_SKIP_CADDY:-0}" == "1" ]]; then
    log "Skipping Caddy install (FS_CORP_SKIP_CADDY=1)"
    return
  fi
  if ! command -v caddy >/dev/null 2>&1; then
    log "Installing caddy package"
    DEBIAN_FRONTEND=noninteractive apt-get install -y caddy
  fi
  log "Installing Caddyfile (companion root ${COMPANION_DIST})"
  local caddy_src="${INSTALL_DIR}/deploy/fs-dev/Caddyfile"
  local caddy_dst=/etc/caddy/Caddyfile
  sed -e "s|/var/lib/fs-corporation/companion/dist|${COMPANION_DIST}|g" \
    "${caddy_src}" > "${caddy_dst}.tmp"
  caddy validate --config "${caddy_dst}.tmp" --adapter caddyfile
  install -o root -g root -m 644 "${caddy_dst}.tmp" "${caddy_dst}"
  rm -f "${caddy_dst}.tmp"
  systemctl enable caddy
  # Never reload: `admin off` disables the API that `caddy reload` posts to, and
  # a failed reload leaves the unit in "reloading" so later reloads block forever.
  systemctl stop caddy || systemctl kill -s SIGKILL caddy || true
  systemctl reset-failed caddy || true
  systemctl start caddy
}

print_caddy_instructions() {
  cat <<EOF

Caddy is installed and started above. To change site addresses later, edit
/etc/caddy/Caddyfile (LAN IP, optional Tailscale IP) and then:
  sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
  sudo systemctl restart caddy
Use restart, not reload: 'admin off' disables the API that reload posts to.

UFW (review deploy/fs-dev/ufw.rules.example before enabling).

Owner token: ${TOKEN_FILE}
Companion URL: https://\${FS_CORP_LAN_IP:-192.168.4.100}/

Container workers:
  sudo -u fs-corp ${INSTALL_DIR}/.venv/bin/python ${INSTALL_DIR}/scripts/verify_fs_dev_workers.py
  sudo -u fs-corp FS_CORP_DB=${DB_PATH} ${INSTALL_DIR}/.venv/bin/python \
    ${INSTALL_DIR}/scripts/exercise_container_dispatch.py \
    --base http://127.0.0.1:8000 \
    --token-file ${TOKEN_FILE} \
    --db ${DB_PATH} \
    --task-id container-pilot-\$(date +%s)

EOF
}

main() {
  require_root
  require_linux
  ensure_user
  ensure_packages
  sync_install_tree
  ensure_venv
  ensure_dirs
  run_migrations
  build_companion
  install_env_example
  configure_gateway_egress
  ensure_docker_access
  build_worker_image
  bootstrap_company
  install_systemd
  install_caddy_site
  print_caddy_instructions
  log "fs-dev install complete"
}

main "$@"
