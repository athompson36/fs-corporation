# fs-dev production hosting (M9)

**Linux only (Debian 12+).** Do not run `install.sh` on macOS or Windows — use [`deploy/dev/README.md`](../dev/README.md) and `docker compose` for local development on your Mac.

Runbook for a single Debian host that runs the FS-Corporation control API on loopback, serves the mobile companion PWA behind Caddy on HTTPS, and optionally builds the isolated Docker worker image.

## Topology

| Role | Address | Notes |
|------|---------|--------|
| LAN edge (Caddy) | `192.168.4.100:443` | TLS (`tls internal`); static companion + `/api/*` proxy |
| Control API | `127.0.0.1:8000` | systemd `fs-corporation-api`; not exposed on LAN |
| Worker NIC (phase 2) | `192.168.4.101` | Reserved for container workers / internal traffic |
| Tailscale | `100.x.x.x` | Optional second `https://` site block in `Caddyfile` |

## Prerequisites

- Debian 12+ (or equivalent) with sudo
- DNS not required for LAN; use static IP `192.168.4.100` on the primary interface
- Optional: [Tailscale](https://tailscale.com/) for off-LAN companion access
- Clone this repository on the host (or rsync from your workstation)

## 1. Configure environment

```bash
sudo mkdir -p /etc/fs-corporation
sudo cp deploy/fs-dev/env.example /etc/fs-corporation/env
sudo chmod 640 /etc/fs-corporation/env
sudo chown root:fs-corp /etc/fs-corporation/env   # after fs-corp user exists
```

Edit `/etc/fs-corporation/env` if paths or IPs differ from defaults.

**Data on fs-dev big disk + Mac SMB:** use [`scripts/deploy_to_fs_dev.sh`](../../scripts/deploy_to_fs_dev.sh) from your Mac. It stages under `~/fs-corporation-deploy` on ext4 (mode 700 — off the SMB share), keeps runtime data on `/Data/fs-corporation/data`, then:

```bash
./scripts/setup_fs_dev_passwordless.sh   # once, after deploy refreshes the sudoers candidate
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
```

That sets `FS_CORP_DATA_DIR=/Data/fs-corporation/data`, binds the data tree into the `fs-dev-data` share (`/Volumes/fs-dev-data/fs-corporation`), and starts Caddy + the API. Worker NIC `192.168.4.101` is already on `eno2`.

Rotate the owner token after any exposure:

```bash
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/rotate-owner-token.sh'
# then store and shred ~/fs-corporation-deploy/owner.token.rotated
```

## 2. Automated install (recommended)

From the **repository root** on the target host:

```bash
sudo deploy/fs-dev/install.sh
```

The script is idempotent: it creates `fs-corp`, installs Python 3.12 venv, `pip install -e .`, runs `alembic upgrade head` against `FS_CORP_DB`, creates `/opt/fs-corporation`, `/var/lib/fs-corporation`, `/etc/fs-corporation`, builds the companion PWA into `FS_CORP_COMPANION_DIST`, installs the systemd unit, and starts `fs-corporation-api`.

## 3. Caddy (HTTPS edge)

`install.sh` installs and **restarts** Caddy (never reload — `admin off` makes reload hang). Edit site addresses in `/etc/caddy/Caddyfile` if the LAN IP changes.

Caddy serves:

- `/` → companion PWA (`FS_CORP_COMPANION_DIST`)
- `/desk` → CEO desk (pairing QR) via the loopback API
- `/api/*` → `127.0.0.1:8000` (SSE-friendly on `/api/v1/events/stream`)

HTTP/3 is disabled on this host because WireGuard (`wg0`) already owns UDP 443.

## 3b. Phone companion + Web Push

1. On a Mac browser open `https://192.168.4.100/desk` (accept the local CA warning).
2. Paste the owner token (from `~/fs-corporation-deploy/owner.token.rotated` or `/etc/fs-corporation/owner.token`), click **Save**.
3. Choose an access level and **Create pairing QR**.
4. On the phone (same LAN), open the `pair_url` / scan the QR, allow notifications when prompted, then **Add to Home Screen**.
5. From the companion, tap **Send test push**, or from the host:

```bash
# As root / with token file readable:
/opt/fs-corporation/.venv/bin/python /opt/fs-corporation/scripts/exercise_push_notify.py \
  --base http://127.0.0.1:8000 \
  --token-file /etc/fs-corporation/owner.token
```

CLI pairing without the desk UI:

```bash
/opt/fs-corporation/.venv/bin/python /opt/fs-corporation/scripts/issue_pairing_ticket.py \
  --token-file /etc/fs-corporation/owner.token
```

## 4. Firewall

Review `deploy/fs-dev/ufw.rules.example`. Goals:

- Allow **22** (SSH) and **443** (HTTPS) on the LAN interface
- Allow **443** on `tailscale0` if using Tailscale
- **Deny 8000** from the LAN so the API cannot be reached off-loopback

```bash
sudo ufw status verbose
```

## 5. Owner token

After install, the bearer token lives at `/etc/fs-corporation/owner.token` (mode `600`, owner `fs-corp`). Configure the companion PWA with this token (local storage / settings screen). Treat it like a root credential.

## 6. Verify

```bash
sudo systemctl status fs-corporation-api
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/health
curl -k -sS -o /dev/null -w "%{http_code}\n" https://192.168.4.100/
```

Run unit tests on a dev machine: `python3 -m unittest discover -s tests -v`.

## 7. Container worker image (phase 2 on-host)

`install.sh` installs Docker, adds `fs-corp` to the `docker` group, creates `/var/lib/fs-corporation/worker-scratch`, builds `fs-corporation-worker:local`, and bootstraps project `app` grants. Ensure `/etc/fs-corporation/env` includes:

```bash
FS_CORP_WORKER_SCRATCH=/var/lib/fs-corporation/worker-scratch
FS_CORP_WORKER_IMAGE=fs-corporation-worker:local
FS_CORP_WORKER_NIC_IP=192.168.4.101   # reserved; same-host dispatch works without binding to this NIC
```

Verify readiness (as `fs-corp`):

```bash
sudo -u fs-corp /opt/fs-corporation/.venv/bin/python /opt/fs-corporation/scripts/verify_fs_dev_workers.py
curl -H "Authorization: Bearer $(sudo cat /etc/fs-corporation/owner.token)" \
  http://127.0.0.1:8000/api/v1/workers/status
```

Exercise a mock container dispatch:

```bash
sudo -u fs-corp FS_CORP_DB=/var/lib/fs-corporation/company.db \
  /opt/fs-corporation/.venv/bin/python /opt/fs-corporation/scripts/exercise_container_dispatch.py \
  --base http://127.0.0.1:8000 \
  --token-file /etc/fs-corporation/owner.token \
  --db /var/lib/fs-corporation/company.db \
  --task-id container-pilot-$(date +%s)
```

Manual image rebuild:

```bash
docker build -f deploy/fs-dev/Dockerfile.worker -t fs-corporation-worker:local .
```

Smoke test with compose (place `envelope.json` in the named volume or bind-mount):

```bash
docker compose -f deploy/fs-dev/docker-compose.workers.yml build
```

Production dispatch uses `docker run` from `company.worker.ContainerWorkerRuntime` and a parent-pumped scratch-directory gateway (`gw-request.json` / `gw-response.json`); see `docs/23-isolated-workers.md`.

## 8. Upgrades

```bash
cd /path/to/checkout
git pull
sudo FS_CORP_INSTALL_DIR=/opt/fs-corporation deploy/fs-dev/install.sh
```

Companion assets are rebuilt; systemd restarts the API.

## Files in this directory

| File | Purpose |
|------|---------|
| `env.example` | Production environment variable template |
| `fs-corporation-api.service` | systemd unit (loopback API) |
| `Caddyfile` | HTTPS reverse proxy + static companion |
| `ufw.rules.example` | Example host firewall rules |
| `install.sh` | Idempotent Debian setup script |
| `Dockerfile.worker` | Python 3.12 worker image |
| `docker-compose.workers.yml` | Local worker image smoke test |

## Limitations

- `--data-dir` on `company.service` is part of the fs-dev contract; ensure the installed package version supports it or align flags with `python -m company.service --help`.
- Container worker `main()` may still be a stub until gateway proxy is fully implemented; subprocess workers remain the dev default.
- Dedicated worker traffic on NIC `192.168.4.101` is documented but not required for same-host dispatch.
- Live GitHub, billing, and model providers remain owner-configured and fail-closed until wired in config.
