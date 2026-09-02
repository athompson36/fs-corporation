# Design: Host gateway egress via worker NIC (.101)

Date: 2026-09-02. Status: approved (approach A).

## Problem

Container workers stay `--network none` and use the scratch-directory gateway. Live outbound calls (model, GitHub, feed, Web Push) leave from the **control API process** (`fs-corp`), which today follows the host default route on `eno1` (`192.168.4.100`). The reserved NIC `eno2` (`192.168.4.101`) is present but unused for egress.

## Decision

Optional **host policy routing** so packets from UID `fs-corp` use routing table `101` with source `FS_CORP_WORKER_NIC_IP` on the matching interface. Workers remain `network_mode=none`. No Docker macvlan/ipvlan.

## Configuration

| Variable | Values | Default |
|---|---|---|
| `FS_CORP_GATEWAY_EGRESS` | `default` \| `worker_nic` | `default` (omit = default) |
| `FS_CORP_WORKER_NIC_IP` | IPv4 on host | required when mode is `worker_nic` |

Fail closed: if mode is `worker_nic` but the IP is missing on a local interface, install reports failure and does not leave a half-applied rule; status reports `egress_active: false`.

## Host mechanism

Script: `deploy/fs-dev/gateway-egress.sh` with `apply` | `remove` | `status`.

- Routing table id **101**, rule priority **1000**, selector `uidrange <fs-corp-uid>-<fs-corp-uid>`.
- Routes in table 101: connected subnet on the worker NIC + `default via <LAN gateway> dev <nic> src <worker_nic_ip>`.
- Idempotent apply/remove.
- `install.sh` calls apply when `FS_CORP_GATEWAY_EGRESS=worker_nic`, otherwise remove (clears stale policy).

Local/`127.0.0.1` stays on the kernel `local` table (priority 0), so the loopback API is unaffected.

## Status API

`GET /api/v1/workers/status` gains a `gateway_egress` object:

```json
{
  "mode": "worker_nic",
  "worker_nic_ip": "192.168.4.101",
  "worker_nic_present": true,
  "egress_active": true,
  "egress_table": 101,
  "egress_source_ip": "192.168.4.101"
}
```

Detection uses read-only `ip rule` / `ip route show table 101` (no root required for status).

## Non-goals

- Worker container networking
- Separate worker host
- Changing gateway allowlist ops
- Binding Caddy or SSH to `.101`

## Acceptance

1. With mode unset: no uid rule for `fs-corp` in table 101; status `mode=default`, `egress_active=false`.
2. With mode `worker_nic` and `.101` present: after install, rule+table exist; status `egress_active=true`.
3. `sudo -u fs-corp ip route get 1.1.1.1` shows `dev eno2` and `src 192.168.4.101`.
4. Unit tests cover status parsing and mode resolution without root.
5. Docs/handoff/roadmap updated; workers still documented as `--network none`.
