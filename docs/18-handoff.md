# Current handoff

Date: 2026-09-02. Version: 0.3.26. State: **fs-dev live; gateway egress via `.101` for `fs-corp`.**

## Delivered

- M9 phase 1 + container default + VAPID contact.
- `FS_CORP_GATEWAY_EGRESS=worker_nic`: policy routing table 101 for UID `fs-corp`
  (source `192.168.4.101` / `eno2`). Workers remain `--network none`.
- `/api/v1/workers/status` → `gateway_egress.{mode,egress_active,egress_source_ip}`.

## Next task

1. Optional: dedicated worker host (separate machine) if same-host egress is not enough.
2. Owner live credential hardening / pilot exercise beyond current secrets path.
3. Furnished HQ room art remains deferred.

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
# expect gateway_egress.egress_active=true
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/workers/status
sudo -u fs-corp ip -4 route get 1.1.1.1   # should show dev eno2 src 192.168.4.101
```

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md) and [superpowers/specs/2026-09-02-gateway-egress-design.md](superpowers/specs/2026-09-02-gateway-egress-design.md).
