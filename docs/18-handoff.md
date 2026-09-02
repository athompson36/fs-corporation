# Current handoff

Date: 2026-09-02. Version: 0.3.15. State: Live GitHub pilot, OpenAI + Anthropic model adapters, RSS/Atom feed poll + HTTP API, Docker dev stack with hot-mounted `company/` + `scripts/`, owner live-config checklist, QR pairing.

## Delivered

- Origin: `https://github.com/athompson36/fs-corporation.git`.
- **Live GitHub:** App configured; project `app` on repo `1354087890`; pilot PR #1.
- **Live models:** `MODEL_PROVIDER_API_KEY` (OpenAI-compatible) and `ANTHROPIC_API_KEY` (Claude `/v1/messages`); `GET /api/v1/model/status`.
- **Live feeds:** `approve_feed_source` / `poll_market_feed`; `GET/POST /api/v1/feeds`, `POST /api/v1/feeds/{id}/poll`.
- Docker: `docker compose up -d --force-recreate`; `PYTHONPATH=/src`; port **8013**.
- Prior: pairing, checklist, cosmic-glass UI, fs-dev runbook.

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_bundle.py
docker compose exec api python scripts/verify_github_app.py
docker compose exec api python scripts/verify_model_provider.py
```

## Limitations

Furnished room interiors deferred. VAPID/Web Push live send unconfigured. Container dispatch on worker NIC `192.168.4.101` not exercised on owner hardware yet.

## Next task

1. **Owner:** run market feed pilot (`POST /api/v1/feeds` + poll GitHub releases atom); rotate API keys if exposed during setup.
2. **Engineering:** exercise `docker compose --profile workers build` and container task dispatch; wire Web Push when VAPID keys supplied.
3. Commit/push v0.3.15 bundle when ready.

## Commands

```bash
docker compose up -d --force-recreate
TOKEN=$(docker compose exec -T api cat /data/owner.token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8013/api/v1/github/status
curl -H "Authorization: Bearer $TOKEN" http://localhost:8013/api/v1/model/status
```

See [../deploy/dev/README.md](../deploy/dev/README.md).
