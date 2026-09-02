# Current handoff

Date: 2026-09-02. Version: 0.3.16. State: Live GitHub, OpenAI + Anthropic models, RSS/Atom feeds + HTTP API, container worker dispatch from Docker dev stack.

## Delivered

- **v0.3.15 pushed** (`b31ae0a`): GitHub App, model providers, feed poll, Docker dev, owner checklist.
- **Container workers (v0.3.16):** Docker CLI + socket in API image, host scratch mount, `scripts/exercise_container_dispatch.py`, dev bootstrap grants for `head`/`app`.
- Live integrations verified on owner Docker stack: GitHub PR, model status, feed ingest, container `runtime=container` → `produced`.

## Verification

```bash
python3 -m unittest discover -s tests -v
docker compose --profile workers build
docker compose up -d --force-recreate
python3 scripts/exercise_container_dispatch.py \
  --token-file <(docker compose exec -T api cat /data/owner.token) \
  --task-id container-pilot-$(date +%s)
```

## Next task

1. **Owner:** rotate API keys if exposed during setup; optional VAPID keys for Web Push.
2. **Engineering:** fs-dev worker NIC `192.168.4.101` production path; Web Push live send.
3. Furnished HQ room art remains deferred.

See [../deploy/dev/README.md](../deploy/dev/README.md).
