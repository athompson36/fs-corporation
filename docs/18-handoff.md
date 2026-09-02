# Current handoff

Date: 2026-09-02. Version: 0.3.24. State: **fs-dev live end-to-end including Apple Web Push `applied`.**

## Delivered

- fs-dev install (ext4 app tree, `/Data` runtime, Caddy HTTPS, workers, desk `/desk`).
- Owner bootstrap/rotation; deploy at `~/fs-corporation-deploy`.
- SQLite request serialization; companion push registration for paired admin devices.
- VAPID PEM loaded via `py_vapid` (raw PEM string broke Apple delivery).
- Companion **Send test push** now reports `applied` / `failed` from delivery records (no more false “sent”).

## Verified on fs-dev (2026-09-02)

| Check | Result |
| --- | --- |
| API + HTTPS edge | 200 |
| Phone companion paired + polling | 200 |
| Apple push subscription | active |
| Host `notify_push` | **`applied`** |
| Container dispatch | produced |

## Next task

1. Optional: set a real `VAPID_CONTACT_EMAIL` in `.env` and redeploy secrets.
2. **M9 phase 2:** container worker traffic on `192.168.4.101` / default production `runtime: container`.
3. Furnished HQ room art remains deferred.

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
```

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
