# Current handoff

Date: 2026-09-02. Version: 0.3.17. State: Live GitHub, OpenAI + Anthropic models, RSS/Atom feeds + HTTP API, container worker dispatch, Web Push (VAPID) adapter.

## Delivered

- **v0.3.15 pushed** (`b31ae0a`): GitHub App, model providers, feed poll, Docker dev, owner checklist.
- **Container workers (v0.3.16):** Docker CLI + socket in API image, host scratch mount, `scripts/exercise_container_dispatch.py`, dev bootstrap grants for `head`/`app`.
- **Web Push (v0.3.17):** `company/push_vapid.py`, live `notify_push` → `applied`/`failed`, `GET /api/v1/push/status`, `scripts/generate_vapid_keys.py`, `scripts/verify_vapid.py`.
- Live integrations verified on owner Docker stack: GitHub PR, model status, feed ingest, container `runtime=container` → `produced`.

## Verification

```bash
python3 -m unittest discover -s tests -v
docker compose --profile workers build
docker compose up -d --force-recreate
python3 scripts/exercise_container_dispatch.py \
  --token-file <(docker compose exec -T api cat /data/owner.token) \
  --task-id container-pilot-$(date +%s)
# After VAPID keys in .env:
python3 scripts/generate_vapid_keys.py   # one-time; paste into .env
docker compose exec api python scripts/verify_vapid.py
```

## Next task

1. **Owner:** rotate API keys if exposed during setup; generate VAPID keys and recreate API container for live push.
2. **Engineering:** fs-dev worker NIC `192.168.4.101` production path.
3. Furnished HQ room art remains deferred.

See [../deploy/dev/README.md](../deploy/dev/README.md).
