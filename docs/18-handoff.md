# Current handoff

Date: 2026-09-02. Version: 0.3.23. State: Local HTTPS edge + CEO test-push API for end-to-end Web Push.

## Delivered

- **v0.3.22** (`bad4736` / `370bdca`): HTTPS Caddy profile, feed poll exercise, verification HTTPS check.
- **v0.3.23:** `POST /api/v1/push/notify`, companion **Send test push**, `scripts/exercise_push_notify.py`.

## Verification

```bash
./scripts/run_all_verifications.sh
./scripts/start_https_dev.sh
# Browser: https://localhost:8443 → owner token → allow notifications → Send test push
python3 scripts/exercise_push_notify.py \
  --token-file <(docker compose exec -T api cat /data/owner.token)
```

## Next task

1. **Owner:** exercise push on `https://localhost:8443`, then Debian fs-dev `install.sh` + secrets export.
2. **Engineering:** production slice on physical host (container dispatch + companion behind Caddy).
3. Furnished HQ room art remains deferred.

See [../deploy/dev/README.md](../deploy/dev/README.md).
