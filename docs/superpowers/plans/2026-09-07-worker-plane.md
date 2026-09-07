# Same-host worker plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose `worker_plane` on `/api/v1/workers/status`, soft verify warnings, and document same-host `.101` plane (v0.3.41).

**Architecture:** Add `worker_plane_summary()` in `company/worker_status.py`; merge into `status_summary()`. Soft mode: plane health never gates `container_dispatch_ready`. Extend verify script with stderr warn + optional `--require-plane`.

**Tech Stack:** Python 3, unittest, existing `host_has_ipv4`.

**Spec:** [docs/superpowers/specs/2026-09-07-worker-plane-design.md](../specs/2026-09-07-worker-plane-design.md)

## Global Constraints

- Soft dispatch: plane never blocks container readiness or `resolve_worker_runtime`
- Keep top-level `worker_nic_ip` / `worker_nic_present` when env set
- `mode` always `"same_host_nic"`
- Version bump to **0.3.41**
- No second-host / DOCKER_HOST / Docker bind to `.101`

## File map

| File | Role |
|---|---|
| `company/worker_status.py` | `worker_plane_summary()` + wire into `status_summary` |
| `tests/test_worker_status.py` | Plane state tests + API asserts `worker_plane` |
| `scripts/verify_fs_dev_workers.py` | Warn / `--require-plane` |
| `docs/23`, `25`, `16`, `14`, `18`, README, spec status | Docs |

---

### Task 1: `worker_plane_summary` + status wire-up

**Files:**
- Modify: `company/worker_status.py`
- Test: `tests/test_worker_status.py`

**Produces:** `worker_plane_summary() -> dict` with keys `mode`, `ip`, `present`, `state`, `reasons`

- [ ] **Step 1: Write failing tests** for healthy / degraded / unset and soft readiness

```python
def test_worker_plane_healthy(self):
    with patch.dict(os.environ, {"FS_CORP_WORKER_NIC_IP": "192.168.4.101"}, clear=False):
        with patch("company.worker_status.host_has_ipv4", return_value=True):
            plane = worker_plane_summary()
    self.assertEqual(plane["mode"], "same_host_nic")
    self.assertEqual(plane["ip"], "192.168.4.101")
    self.assertTrue(plane["present"])
    self.assertEqual(plane["state"], "healthy")
    self.assertEqual(plane["reasons"], [])

def test_worker_plane_degraded(self):
    with patch.dict(os.environ, {"FS_CORP_WORKER_NIC_IP": "192.168.4.101"}, clear=False):
        with patch("company.worker_status.host_has_ipv4", return_value=False):
            plane = worker_plane_summary()
    self.assertEqual(plane["state"], "degraded")
    self.assertFalse(plane["present"])
    self.assertIn("worker NIC IP not on host", plane["reasons"])

def test_worker_plane_unset(self):
    with patch.dict(os.environ, {"FS_CORP_WORKER_NIC_IP": ""}, clear=False):
        plane = worker_plane_summary()
    self.assertEqual(plane["state"], "unset")
    self.assertIsNone(plane["ip"])
    self.assertFalse(plane["present"])
    self.assertIn("FS_CORP_WORKER_NIC_IP unset", plane["reasons"])

def test_degraded_plane_does_not_block_container_ready(self):
    # scratch+docker+image ok, plane degraded → container_dispatch_ready True
    ...
```

Also assert `status_summary()["worker_plane"]` and API response includes `worker_plane`.

- [ ] **Step 2: Run** `.venv/bin/python -m unittest tests.test_worker_status -v` — expect FAIL (import/missing key)

- [ ] **Step 3: Implement**

```python
def worker_plane_summary() -> dict:
    worker_nic = (os.environ.get("FS_CORP_WORKER_NIC_IP") or "").strip()
    if not worker_nic:
        return {
            "mode": "same_host_nic",
            "ip": None,
            "present": False,
            "state": "unset",
            "reasons": ["FS_CORP_WORKER_NIC_IP unset"],
        }
    present = host_has_ipv4(worker_nic)
    if present:
        return {
            "mode": "same_host_nic",
            "ip": worker_nic,
            "present": True,
            "state": "healthy",
            "reasons": [],
        }
    return {
        "mode": "same_host_nic",
        "ip": worker_nic,
        "present": False,
        "state": "degraded",
        "reasons": ["worker NIC IP not on host"],
    }
```

In `status_summary()`, set `out["worker_plane"] = worker_plane_summary()` always (before or after nic flat fields; do not use plane for `container_dispatch_ready`).

- [ ] **Step 4: Re-run tests** — expect PASS

---

### Task 2: Verify script

**Files:**
- Modify: `scripts/verify_fs_dev_workers.py`
- Optional test: argparse/`main` via unittest or doctest-style in `tests/test_worker_status.py`

- [ ] **Step 1:** Extend script:

```python
def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-plane", action="store_true")
    args = parser.parse_args(argv)
    summary = status_summary()
    print(json.dumps(summary, indent=2))
    plane = summary.get("worker_plane") or {}
    if plane.get("state") != "healthy":
        print(f"warning: worker_plane state={plane.get('state')} reasons={plane.get('reasons')}", file=sys.stderr)
        if args.require_plane:
            return 3
    return 0 if summary.get("container_dispatch_ready") else 2
```

- [ ] **Step 2:** Manual: `.venv/bin/python scripts/verify_fs_dev_workers.py --help`

---

### Task 3: Docs + version 0.3.41

**Files:** `pyproject.toml`, `company/__init__.py` (if version there), `docs/16-api-contract.md`, `docs/23-isolated-workers.md`, `docs/25-fs-dev-deployment.md`, `docs/14-roadmap.md`, `docs/18-handoff.md`, `README.md`, spec status → implemented

- [ ] Update contract line for `/workers/status` to mention `worker_plane`
- [ ] Clarify same-host plane vs future second host in 23/25
- [ ] Handoff next = TailscaleKit / ChatDev deps / second host still optional

---

### Task 4: Bundle check

```bash
.venv/bin/python -m unittest tests.test_worker_status -v
python3 scripts/check_bundle.py
```
