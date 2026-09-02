# Current handoff

Date: 2026-09-02. Version: 0.3.20. State: Live integrations on Docker dev; companion PWA registers Web Push when VAPID is configured.

## Delivered

- **v0.3.19** (`9472aef`): `run_all_verifications.sh`, clearer model errors, host-side config path resolution.
- **Companion push (v0.3.20):** `application_server_key` on `GET /api/v1/push/status`, service worker push handler, auto-registration from Settings when owner token is set.

## Verification

```bash
./scripts/run_all_verifications.sh
cd companion && npm run build
# Companion dev (API CORS on 5173 when FS_CORP_ALLOW_CORS=1):
# VITE_API_BASE=http://localhost:8013 npm run dev
```

## Next task

1. **Owner:** run `install.sh` on Debian fs-dev host (`192.168.4.100`); copy secrets to `/etc/fs-corporation/secrets.env`.
2. **Engineering:** end-to-end push test in browser with companion on HTTPS (LAN Caddy) or localhost.
3. Furnished HQ room art remains deferred.

See [../deploy/dev/README.md](../deploy/dev/README.md).
