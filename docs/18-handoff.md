# Current handoff

Date: 2026-09-01. Version: 0.3.9. State: loopback control service, mobile CEO companion (M8) including fail-closed Web Push, fs-dev deployment runbook (M9), GitHub effect lifecycle (M4), market feed poll lifecycle (M5), and container worker file gateway. Live adapters remain disabled.

## Delivered

- Origin remote is `https://github.com/athompson36/fs-corporation.git`.
- Nested M0–M9 checklists in docs/14-roadmap.md. ADR-010–016.
- Alembic revisions through `0008_push_notifications`.
- `register_push_subscription` / `revoke_push_subscription` / `notify_push`: CEO HTTPS enrollment; live send `live_unavailable`; owner-inbox create attempts delivery. PWA still polls every 15s.
- Prior: GitHub `apply_github_effect`, feed `poll_market_feed`, container scratch-directory gateway, companion PWA, fs-dev runbook.

## Verification

**86 unit tests** pass in `.venv` after `pip install -e .`, including `tests/test_push.py`. `python3 scripts/check_bundle.py` passes.

## Limitations

No live Web Push (no VAPID). No isometric HQ art. SLOs unmeasured until production load. Live GitHub/model/feed and container dispatch on `192.168.4.101` still need owner credentials.

## Next task

Owner-supplied live configuration: GitHub App + disposable repo IDs, model credential, approved feed URL, optional VAPID keys. Build `fs-corporation-worker:local` and exercise container dispatch on `192.168.4.101`. Remaining local decorative/ops items: isometric HQ art (style undecided) and measured SLOs.

## Commands

```bash
python3 -m company.service --host 127.0.0.1 --port 8000
python3 -m company.service --host $(tailscale ip -4) --port 8000 --allow-remote
cd companion && npm run dev
sudo deploy/fs-dev/install.sh
python3 -m unittest discover -s tests -v
```
