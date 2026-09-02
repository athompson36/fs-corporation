# Current handoff

Date: 2026-09-02. Version: 0.3.23. State: **fs-dev live end-to-end including Apple Web Push `applied`.**

## Delivered

- fs-dev install (ext4 app tree, `/Data` runtime, Caddy HTTPS, workers, desk `/desk`).
- Owner bootstrap/rotation; deploy at `~/fs-corporation-deploy`.
- SQLite request serialization; companion push registration for paired admin devices.
- VAPID PEM loaded via `py_vapid` (raw PEM string broke Apple delivery).

## Verified on fs-dev (2026-09-02)

| Check | Result |
| --- | --- |
| API + HTTPS edge | 200 |
| Phone companion paired + polling | 200 |
| Apple push subscription | active |
| Host `notify_push` after VAPID fix | **`applied`** (`Host push verify …`) |
| Container dispatch | produced |

## Next task

1. Confirm the phone showed the OS notification for `Host push verify …` (and/or tap
   **Send test push** once more from Settings).
2. Optional: set a real `VAPID_CONTACT_EMAIL` in `.env` (still `mailto:owner@example.com`).
3. Furnished HQ room art remains deferred.

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
```

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
