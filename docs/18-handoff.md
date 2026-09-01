# Current handoff

Date: 2026-09-01. Version: 0.3.6. State: loopback control service, mobile CEO companion (M8), and fs-dev deployment runbook (M9). Dashboard APIs, owner inbox, project dispatch-brief, SSE, PWA over LAN HTTPS and Tailscale. Native systemd API + Caddy edge; Docker worker scaffold only. Subprocess-isolated workers, QC/HR gates, and employee development remain in place. Live adapters remain disabled.

## Delivered

- Project/folder name is **fs-corporation** (workspace `fs-corporation.code-workspace`; no leftover `fs-tech-ai-company` workspace). Token hash prefix is `fs-corporation-identity:` — existing local owner tokens issued under the old prefix will not match until re-registered.
- Nested M0–M9 checklists in docs/14-roadmap.md. ADR-010–016.
- Alembic revisions through `0006_mobile_companion`.
- Mobile companion: `GET /api/v1/dashboard`, projects, decisions inbox, owner inbox, dispatch-brief, SSE stream.
- PWA in `companion/`; Expo shell scaffold in `companion-native/`.
- fs-dev deployment: `deploy/fs-dev/` (`install.sh`, systemd unit, Caddyfile, ufw example, worker Dockerfile/compose scaffold).
- Canonical runbook: docs/25-fs-dev-deployment.md (LAN `192.168.4.100`, reserved `.101` phase 2).

## Verification

**74 unit tests** pass in `.venv` after `pip install -e .`, including `tests/test_companion_api.py` and `tests/test_owner_requests.py`. `python3 scripts/check_bundle.py` passes. Companion PWA: `cd companion && npm install && npm run build`.

## Limitations

Loopback API in production; remote access is via Caddy HTTPS on LAN/Tailscale, not raw port 8000. Dev `--allow-remote` bind remains Tailscale-only. Push notifications not implemented. Expansion decisions from mobile show a message to use CEO desk. Subprocess workers are not a malicious-code sandbox. Container workers and live adapters still fail-closed until owner credentials on `.101`.

## Next task

Owner-supplied live configuration: GitHub App + repo IDs, model credential for worker/gateway, optional feed. Build and exercise container worker image on reserved host `192.168.4.101`. Optional: push notifications for owner inbox.

## Commands

```bash
python3 -m company.service --host 127.0.0.1 --port 8000
python3 -m company.service --host $(tailscale ip -4) --port 8000 --allow-remote
cd companion && npm run dev
sudo deploy/fs-dev/install.sh
python3 -m unittest discover -s tests -v
```
