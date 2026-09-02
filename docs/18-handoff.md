# Current handoff

Date: 2026-09-02. Version: 0.3.23. State: **fs-dev live end-to-end** — companion paired, Web Push subscribed, test notify recorded.

## Delivered

- fs-dev install (ext4 app tree, data on `/Data`, Caddy HTTPS, workers).
- Owner bootstrap/rotation; deploy tree at `~/fs-corporation-deploy`.
- CEO desk at `https://192.168.4.100/desk`; companion PWA at `/`.
- SQLite request serialization; companion push registration for paired admin devices.
- iOS A2HS guidance + Enable push control.

## Verified on fs-dev (2026-09-02)

| Check | Result |
| --- | --- |
| API + HTTPS edge | 200 |
| Phone companion poll | 200 |
| Active push subscription | 1 |
| Companion “Send test push” | sent (check delivery status in DB/journal) |
| Container dispatch | produced earlier this session |

## Next task

1. Confirm the OS notification actually appeared on the phone (if not, check Focus/DND and delivery `status` in `push_deliveries`).
2. Optional: set a real `VAPID_CONTACT_EMAIL` in `.env` (still placeholder) and redeploy secrets.
3. Furnished HQ room art remains deferred.

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
```

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
