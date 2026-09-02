# Current handoff

Date: 2026-09-02. Version: 0.3.25. State: **fs-dev live; same-host M9 phase 2 defaults enabled** (container runtime + `.101` NIC check).

## Delivered

- Phase 1: install, Caddy, companion, pairing, Apple Web Push `applied`.
- Phase 2 (same-host): `FS_CORP_DEFAULT_WORKER_RUNTIME=container` (fail-closed if not ready),
  `worker_nic_present` for `192.168.4.101`, Docker labels `fs.corp.runtime` / `fs.corp.worker_nic`.
  Workers remain `--network none` (scratch gateway only).

## Next task

1. Optional: real `VAPID_CONTACT_EMAIL` in `.env`.
2. Follow-on: dedicated worker host / egress policy on `.101` if needed beyond labels+presence.
3. Furnished HQ room art remains deferred.

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/workers/status
```

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
