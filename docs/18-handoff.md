# Current handoff

Date: 2026-09-02. Version: 0.3.22. State: Local HTTPS dev profile for Web Push; automated feed poll exercise.

## Delivered

- **v0.3.21** (`d2e91ab`): Push subscription list API, `verify_push_delivery.py`, `export_fs_dev_secrets.sh`.
- **v0.3.22:** Docker `https` profile (Caddy on `https://localhost:8443`), `scripts/exercise_feed_poll.py`.

## Verification

```bash
./scripts/run_all_verifications.sh
cd companion && npm run build && cd ..
docker compose --profile https up -d
open https://localhost:8443   # owner token in Settings → push on secure context
```

## Next task

1. **Owner:** Debian fs-dev at `192.168.4.100` — `install.sh` + secrets from `export_fs_dev_secrets.sh`.
2. **Owner:** test live push on `https://localhost:8443` (Mac) or `https://192.168.4.100` (fs-dev).
3. Furnished HQ room art remains deferred.

See [../deploy/dev/README.md](../deploy/dev/README.md).
