# Current handoff

Date: 2026-09-01. Version: 0.3.14. State: QR pairing with scoped access levels (read only / user / admin), Tailscale handoff on redeem, companion auto-redeem and scope-gated UI, cosmic-glass desk/companion, room detail, isometric HQ, sourced SLO catalog, fail-closed Web Push, GitHub/feed/container lifecycles, fs-dev runbook. Live adapters remain disabled.

## Delivered

- Origin: `https://github.com/athompson36/fs-corporation.git`.
- Alembic through `0011_pairing_access_level`.
- QR pairing (ADR-018): CEO desk level picker, one-time tickets, companion `#fs-pair` auto-redeem, scoped service principals (never root owner token).
- Optional `FS_CORP_PUBLIC_URL`, `FS_CORP_TAILSCALE_AUTHKEY` (redeem only), `FS_CORP_ALLOW_CORS` for dev preview.
- Prior: cosmic-glass UI, room detail, isometric HQ, SLO catalog, Web Push, GitHub apply, feed poll, container file gateway, companion PWA, fs-dev.

## Verification

Run in `.venv` after `pip install -e .`:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_bundle.py
cd companion && npm run build
```

Pairing tests cover level scopes, deny approve/pause for read_only/user, and auth key only on redeem.

## Limitations

Furnished room interiors are deferred. SLOs have no production samples. Live GitHub/model/feed/VAPID and container dispatch on `192.168.4.101` still need owner credentials. PWA cannot join Tailscale kernel VPN; paired-device revocation UI is deferred.

## Next task

Owner-supplied live configuration on fs-dev: GitHub App + repo IDs, model credential, approved feed, optional VAPID. Build and exercise `fs-corporation-worker:local` on `192.168.4.101`.

## Commands

```bash
python3 -m company.service --host 127.0.0.1 --port 8000
python3 -m unittest discover -s tests -v
```
