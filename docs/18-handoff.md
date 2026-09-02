# Current handoff

Date: 2026-09-01. Version: 0.3.8. State: loopback control service, mobile CEO companion (M8), fs-dev deployment runbook (M9), GitHub effect lifecycle (M4), market feed poll lifecycle (M5), and container worker file gateway. Dashboard APIs, owner inbox, project dispatch-brief, SSE, PWA over LAN HTTPS and Tailscale. Native systemd API + Caddy edge. Subprocess-isolated workers, QC/HR gates, and employee development remain in place. Live adapters remain disabled.

## Delivered

- Project/folder name is **fs-corporation**. Origin remote is `https://github.com/athompson36/fs-corporation.git`.
- Nested M0–M9 checklists in docs/14-roadmap.md. ADR-010–016.
- Alembic revisions through `0007_feed_polls`.
- Mobile companion: dashboard, projects, decisions inbox, owner inbox, dispatch-brief, SSE, PWA.
- fs-dev deployment: `deploy/fs-dev/` plus docs/25-fs-dev-deployment.md.
- `Company.apply_github_effect`: authorize, idempotent record, fail-closed live write (`live_unavailable`).
- `Company.approve_feed_source` / `poll_market_feed`: CEO HTTPS enrollment, idempotent poll, fail-closed live fetch; no invented signals or policy change.
- Container runtime: `python -m company.worker --envelope/--scratch` with parent-pumped `gw-request.json` / `gw-response.json` on the scratch volume.

## Verification

**80 unit tests** pass in `.venv` after `pip install -e .`, including `tests/test_m5.py` feed lifecycle, `tests/test_workers.py` container file gateway, `tests/test_m4.py`, `tests/test_companion_api.py` and `tests/test_owner_requests.py`. `python3 scripts/check_bundle.py` passes.

## Limitations

Loopback API in production; remote access is via Caddy HTTPS on LAN/Tailscale, not raw port 8000. Push notifications not implemented. Expansion decisions from mobile show a message to use CEO desk. Subprocess workers are not a malicious-code sandbox. Live adapters and production container dispatch on `192.168.4.101` still need owner credentials. Feed poll and GitHub apply do not fetch or push.

## Next task

Owner-supplied live configuration: GitHub App + disposable repo IDs, model credential for worker/gateway, approved feed URL if market polling is required. Build `fs-corporation-worker:local` and exercise container dispatch on reserved host `192.168.4.101`. Optional: push notifications for owner inbox.

## Commands

```bash
python3 -m company.service --host 127.0.0.1 --port 8000
python3 -m company.service --host $(tailscale ip -4) --port 8000 --allow-remote
cd companion && npm run dev
sudo deploy/fs-dev/install.sh
python3 -m unittest discover -s tests -v
```
