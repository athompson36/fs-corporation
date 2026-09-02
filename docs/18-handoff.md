# Current handoff

Date: 2026-09-02. Version: 0.3.21. State: Push delivery verify script, subscription list API, fs-dev secrets export helper.

## Delivered

- **v0.3.20** (`36e9efa`): Companion Web Push auto-registration + `application_server_key`.
- **v0.3.21:** `GET /api/v1/push/subscriptions`, `scripts/verify_push_delivery.py`, `scripts/export_fs_dev_secrets.sh` for Debian host migration.

## Verification

```bash
./scripts/run_all_verifications.sh
docker compose exec api python scripts/verify_push_delivery.py
./scripts/export_fs_dev_secrets.sh   # owner: prepare fs-dev secrets.env
cd companion && VITE_API_BASE=http://localhost:8013 npm run dev
```

## Next task

1. **Owner:** Debian fs-dev at `192.168.4.100` — `sudo deploy/fs-dev/install.sh`, copy secrets from `export_fs_dev_secrets.sh`, test companion at `https://192.168.4.100`.
2. **Engineering:** live browser push on HTTPS (requires Caddy + companion build on host).
3. Furnished HQ room art remains deferred.

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
