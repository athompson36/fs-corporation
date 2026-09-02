# Gateway egress via .101 — Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox syntax.

**Goal:** Opt-in host policy routing so the `fs-corp` API egresses via `192.168.4.101` without giving containers a network.

**Architecture:** Shell script manages `ip rule`/`ip route` table 101 for the service UID; `company.worker_status` reports mode and whether the rule is active; install applies or removes based on `FS_CORP_GATEWAY_EGRESS`.

**Tech Stack:** bash, `iproute2`, Python status probes, existing fs-dev install path.

## Global Constraints

- Workers remain `--network none`.
- Fail closed when `worker_nic` mode is set but NIC IP is absent.
- Do not put secrets or root scripts on the NTFS `/Data` share.
- Version bump when shipping.

---

### Task 1: Status + tests

- [ ] Extend `company/worker_status.py` with `gateway_egress_summary()` and nest under `status_summary()`.
- [ ] Tests in `tests/test_worker_status.py` for mode default/worker_nic and mocked `ip` output.

### Task 2: Host script + install

- [ ] Add `deploy/fs-dev/gateway-egress.sh` (`apply`/`remove`/`status`).
- [ ] Hook from `install.sh`; wire `FS_CORP_GATEWAY_EGRESS=worker_nic` in `env.example` + `deploy_to_fs_dev.sh`.

### Task 3: Docs + ship

- [ ] Update docs 18/14/23/25, decisions, README capability note; version `0.3.26`.
- [ ] Deploy to fs-dev and verify `egress_active` + `ip route get` as `fs-corp`.
