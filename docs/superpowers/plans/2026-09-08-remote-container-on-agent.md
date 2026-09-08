# Remote Container-on-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Opt-in remote pull agents run the worker Docker image with `--network none`, relay allowlisted file-gateway ops to the control plane, and complete jobs fail-closed when Docker/image is missing.

**Architecture:** Claim returns a `build_worker_envelope` payload. Agent (when `FS_CORP_REMOTE_WORKER_RUNTIME=container`) writes scratch, runs the worker image, pumps `gw-request.json` via new host-token `gateway` / `renew` routes that reuse `SubprocessWorkerRuntime.handle_request`. Default agent path stays mock-complete. No new Alembic revision.

**Tech Stack:** Python 3, existing FastAPI `company/service.py`, `company/remote_jobs.py`, `company/worker.py`, `scripts/remote_worker_agent.py`, unittest.

## Global Constraints

- Version bump to **0.3.58**; ADR-044; no Alembic (HEAD stays `0028_remote_worker_jobs`).
- Container network: always `--network none` (no ChatDev egress on remote this slice).
- Activation: agent env `FS_CORP_REMOTE_WORKER_RUNTIME=container` only; default mock.
- Missing docker/image in container mode → `complete` with `status=failed`; never silent mock.
- `store_artifact` on gateway must ignore container `/work` paths; use control-plane artifact root for the task.
- Do not commit `local repos/service-department/`.
- Prefer branch `feature/remote-container-on-agent` from `main` (B merge optional).

## File map

| File | Responsibility |
|---|---|
| `company/remote_jobs.py` | `claim_job` adds `envelope`; `relay_gateway`; `renew_job_lease`; optional runtime on complete |
| `company/core.py` | Thin wrappers for new remote job methods |
| `company/service.py` | HTTP routes for gateway + renew; complete may pass `runtime` |
| `scripts/remote_worker_agent.py` | Container execute + pump; mock unchanged |
| `tests/test_remote_container_agent.py` | New tests for envelope, gateway, renew, agent helpers |
| `docs/decisions.md`, `docs/16-api-contract.md`, `docs/18-handoff.md`, `docs/14-roadmap.md`, version files | Ship docs |

---

### Task 1: Claim returns envelope

**Files:**
- Modify: `company/remote_jobs.py` (`claim_job`)
- Modify: `tests/test_remote_worker_jobs.py` (or extend new test module)
- Test: `tests/test_remote_container_agent.py`

**Interfaces:**
- Consumes: `build_worker_envelope(company, worker_id, task_id, approval=None) -> dict` from `company.worker`
- Produces: `claim_job(...)` return dict includes `envelope` with keys `worker_id`, `task_id`, `payload`, `workflow_digest`, `approval`

- [ ] **Step 1: Write the failing test**

Create `tests/test_remote_container_agent.py`:

```python
"""Remote container-on-agent: envelope, gateway relay, renew."""
import unittest
from company.core import Company
from company.remote_jobs import claim_job, enqueue_remote_job
from company.worker_hosts import create_worker_host, record_worker_host_heartbeat
from tests.test_core import install, policy


class ClaimEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        created = create_worker_host(
            self.c, "human-ceo", label="lab", base_url="https://lab.example.com"
        )
        self.host_id = created["id"]
        self.token = created["token"]
        record_worker_host_heartbeat(self.c, self.host_id, self.token)
        self.c.queue_task("head", "app", "draft", 10, "env-t1")

    def test_claim_includes_envelope(self):
        job = enqueue_remote_job(
            self.c, "human-ceo",
            host_id=self.host_id, task_id="env-t1", worker_id="worker-r",
        )
        claimed = claim_job(self.c, self.host_id, self.token, job["id"])
        env = claimed["envelope"]
        self.assertEqual(env["task_id"], "env-t1")
        self.assertEqual(env["worker_id"], f"remote-host:{self.host_id}")
        self.assertIn("payload", env)
        self.assertIn("workflow_digest", env)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_remote_container_agent.ClaimEnvelopeTests -v`  
Expected: FAIL (`KeyError: 'envelope'` or assert).

- [ ] **Step 3: Implement claim envelope**

In `claim_job`, after building `out = _job_public(row)` and loading queue `payload`, add:

```python
from company.worker import build_worker_envelope

# worker_id used at enqueue is remote-host:{host_id}; rebuild from job row
worker_id = f"remote-host:{host_id}"
out["envelope"] = build_worker_envelope(company, worker_id, row["task_id"])
```

If `build_worker_envelope` rejects `leased` ownership mismatch, ensure enqueue still leases as `remote-host:{host_id}` (already true) so claim succeeds.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_remote_container_agent.ClaimEnvelopeTests -v`  
Expected: PASS

- [ ] **Step 5: Commit** (when owner asks, or per executing-plans policy)

```bash
git add company/remote_jobs.py tests/test_remote_container_agent.py
git commit -m "$(cat <<'EOF'
Return worker envelope on remote job claim.

EOF
)"
```

---

### Task 2: Gateway relay + lease renew

**Files:**
- Modify: `company/remote_jobs.py`
- Modify: `company/core.py` (wrappers)
- Modify: `company/service.py` (routes)
- Test: `tests/test_remote_container_agent.py`

**Interfaces:**
- Produces:
  - `relay_gateway(company, host_id, token, job_id, message: dict) -> dict`
  - `renew_job_lease(company, host_id, token, job_id) -> dict` (public job fields + new `lease_expires_at`)
- Gateway successful path renews lease by `LEASE_SEC`
- `store_artifact`: pass `artifact_root` = control-plane path under company data/artifacts for `task_id` (create dir); do not use message `root` if it looks like `/work` or is absolute under container

- [ ] **Step 1: Write failing tests**

```python
from datetime import timedelta
from company.core import now
from company.remote_jobs import claim_job, enqueue_remote_job, relay_gateway, renew_job_lease


class GatewayRelayTests(unittest.TestCase):
    def setUp(self):
        # same host/task setup as ClaimEnvelopeTests; queue task gw-t1
        ...

    def _claimed(self):
        job = enqueue_remote_job(
            self.c, "human-ceo",
            host_id=self.host_id, task_id="gw-t1", worker_id="worker-r",
        )
        return claim_job(self.c, self.host_id, self.token, job["id"])

    def test_gateway_check_allowed(self):
        claimed = self._claimed()
        reply = relay_gateway(
            self.c, self.host_id, self.token, claimed["id"],
            {
                "op": "gateway_check",
                "actor": "head",
                "project": "app",
                "action": "draft",
                "cost": 10,
                "task_id": "gw-t1",
            },
        )
        self.assertTrue(reply.get("allow"))

    def test_gateway_unknown_op_denied(self):
        claimed = self._claimed()
        with self.assertRaises(PermissionError):
            relay_gateway(
                self.c, self.host_id, self.token, claimed["id"],
                {"op": "delete_database"},
            )

    def test_renew_extends_lease(self):
        claimed = self._claimed()
        before = claimed["lease_expires_at"]
        renewed = renew_job_lease(self.c, self.host_id, self.token, claimed["id"])
        self.assertGreaterEqual(renewed["lease_expires_at"], before)

    def test_gateway_rejects_expired_lease(self):
        claimed = self._claimed()
        past = (now() - timedelta(seconds=5)).isoformat()
        with self.c.tx():
            self.c.db.execute(
                "UPDATE remote_worker_jobs SET lease_expires_at=? WHERE id=?",
                (past, claimed["id"]),
            )
        with self.assertRaises(PermissionError):
            relay_gateway(
                self.c, self.host_id, self.token, claimed["id"],
                {
                    "op": "gateway_check",
                    "actor": "head", "project": "app", "action": "draft",
                    "cost": 10, "task_id": "gw-t1",
                },
            )
```

- [ ] **Step 2: Run tests — expect FAIL** (functions missing)

Run: `.venv/bin/python -m unittest tests.test_remote_container_agent.GatewayRelayTests -v`

- [ ] **Step 3: Implement `renew_job_lease` and `relay_gateway`**

```python
def _require_claimed_lease(company, host_id, token, job_id):
    require_host_token(company, host_id, token)
    stamp = now().isoformat()
    _expire_stale_claims(company, host_id)  # only inside tx callers
    row = company.db.execute(
        "SELECT * FROM remote_worker_jobs WHERE id=? AND host_id=?",
        (job_id, host_id),
    ).fetchone()
    if not row:
        raise PermissionError("Unknown remote job")
    if row["status"] != "claimed":
        raise PermissionError("Job is not claimed")
    if row["lease_expires_at"] and row["lease_expires_at"] < stamp:
        raise PermissionError("Job lease expired")
    return row


def renew_job_lease(company, host_id: str, token: str, job_id: str) -> dict:
    require_host_token(company, host_id, token)
    stamp = now().isoformat()
    expires = (now() + timedelta(seconds=LEASE_SEC)).isoformat()
    with company.tx():
        _expire_stale_claims(company, host_id)
        row = _require_claimed_lease(company, host_id, token, job_id)
        # Note: _require_claimed_lease must not open a nested tx; inline checks instead if needed
        company.db.execute(
            "UPDATE remote_worker_jobs SET lease_expires_at=?, updated_at=? WHERE id=?",
            (expires, stamp, job_id),
        )
        company._event("remote_job.lease_renewed", {"id": job_id, "host_id": host_id})
    row = company.db.execute(
        "SELECT * FROM remote_worker_jobs WHERE id=?", (job_id,)
    ).fetchone()
    return _job_public(row)


def relay_gateway(company, host_id: str, token: str, job_id: str, message: dict) -> dict:
    from company.worker import SubprocessWorkerRuntime
    from pathlib import Path
    require_host_token(company, host_id, token)
    stamp = now().isoformat()
    expires = (now() + timedelta(seconds=LEASE_SEC)).isoformat()
    with company.tx():
        _expire_stale_claims(company, host_id)
        row = company.db.execute(
            "SELECT * FROM remote_worker_jobs WHERE id=? AND host_id=?",
            (job_id, host_id),
        ).fetchone()
        if not row:
            raise PermissionError("Unknown remote job")
        if row["status"] != "claimed":
            raise PermissionError("Job is not claimed")
        if row["lease_expires_at"] and row["lease_expires_at"] < stamp:
            raise PermissionError("Job lease expired")
        company.db.execute(
            "UPDATE remote_worker_jobs SET lease_expires_at=?, updated_at=? WHERE id=?",
            (expires, stamp, job_id),
        )
    task_id = row["task_id"]
    # Control-plane artifact dir — never agent /work. Prefer FS_CORP_WORKER_SCRATCH.
    import os, tempfile
    base = (os.environ.get("FS_CORP_WORKER_SCRATCH") or "").strip()
    if base:
        artifact_root = Path(base) / "remote-artifacts" / task_id
    else:
        artifact_root = Path(tempfile.mkdtemp(prefix=f"remote-art-{task_id}-"))
    artifact_root.mkdir(parents=True, exist_ok=True)
    msg = dict(message)
    if str(msg.get("root") or "").startswith("/work"):
        msg.pop("root", None)
    return SubprocessWorkerRuntime.handle_request(
        company, msg, approval=None, artifact_root=str(artifact_root),
    )
```

Wire `company.gateway_remote_job` / `company.renew_remote_job` in `core.py`.

Add routes next to claim/complete in `service.py` for `gateway` and `renew` (same host-token auth pattern as claim).

- [ ] **Step 4: Run tests — expect PASS**

Run: `.venv/bin/python -m unittest tests.test_remote_container_agent.GatewayRelayTests -v`

- [ ] **Step 5: Commit** when appropriate

---

### Task 3: Complete may set `remote_container` runtime

**Files:**
- Modify: `company/remote_jobs.py` `complete_job`
- Modify: `company/service.py` complete handler to pass `runtime` from body
- Test: `tests/test_remote_container_agent.py`

**Interfaces:**
- `complete_job(..., status, result=None, runtime: str | None = None)`
- Allowed override values: `remote_container` only (ignore/reject others with ValueError, or ignore silently — prefer **ValueError** if present and not in `{None, "remote_agent", "remote_container"}`)
- On success/failure, if `runtime == "remote_container"`, `UPDATE worker_runs SET runtime=?` for that run

- [ ] **Step 1: Failing test** — complete with `runtime="remote_container"` updates `worker_runs.runtime`

- [ ] **Step 2: Implement + pass**

- [ ] **Step 3: Commit** when appropriate

---

### Task 4: Agent container path

**Files:**
- Modify: `scripts/remote_worker_agent.py`
- Test: `tests/test_remote_container_agent.py` (unit-test helpers; do not require live Docker)

**Interfaces / helpers to extract for testability:**
- `runtime_mode() -> str` from `FS_CORP_REMOTE_WORKER_RUNTIME`
- `docker_ready(image: str, docker_bin: str | None = None) -> tuple[bool, str]` — False + reason if no docker or `docker image inspect` fails
- `build_docker_cmd(docker, image, scratch: Path) -> list[str]` — always includes `--network`, `none`
- `pump_remote_gateway(scratch, post_gateway, renew, timeout=120)` — loop like `pump_file_gateway` but callbacks instead of Company
- `execute_claimed_job(base, host_id, token, claimed) -> tuple[str, dict]` — returns `("completed"|"failed", result)`

Behavior in `once()`:
1. Claim as today
2. If `runtime_mode() != "container"`: mock_execute + complete completed
3. Else if not `docker_ready`: complete **failed** with `result={"error": reason, "type": "remote_container_unready"}`
4. Else: write envelope, Popen docker, pump with HTTP post to gateway/renew, communicate; on success complete with `runtime=remote_container`; on error complete failed

```python
def build_docker_cmd(docker: str, image: str, scratch: Path) -> list[str]:
    mount = str(scratch.resolve())
    return [
        docker, "run", "--rm", "--network", "none",
        "-v", f"{mount}:/work:rw",
        "-e", "COMPANY_WORKER_MODE=container",
        "--label", "fs.corp.runtime=remote_container",
        "--label", "fs.corp.network=none",
        image,
        "--envelope", "/work/envelope.json",
        "--scratch", "/work",
    ]
```

- [ ] **Step 1: Tests for `docker_ready` false, `build_docker_cmd` contains `--network`/`none`, mock path still returns remote_mock type**

- [ ] **Step 2: Implement agent helpers + wire `once`**

- [ ] **Step 3: Run** `.venv/bin/python -m unittest tests.test_remote_container_agent -v` **PASS**

- [ ] **Step 4: Commit** when appropriate

---

### Task 5: Docs, version, ADR, verification

**Files:**
- Modify: `company/__init__.py` → `0.3.58`
- Modify: companion / README / VERIFICATION version strings if they track app version (match prior 0.3.57 bump pattern)
- Modify: `docs/decisions.md` ADR-044
- Modify: `docs/16-api-contract.md` (gateway, renew, claim envelope, complete runtime)
- Modify: `docs/18-handoff.md`, `docs/14-roadmap.md`
- Spec status → implemented when done

ADR-044 summary:
> Remote agents may opt into container execution with `--network none` and host-token gateway relay; default remains mock-complete; no remote egress this slice.

- [ ] **Step 1: Apply doc/version edits**

- [ ] **Step 2: Full suite**

Run: `.venv/bin/python -m unittest discover -s tests`  
Expected: all PASS (update HEAD revision asserts only if you added a migration — you should not)

- [ ] **Step 3: Commit** when owner asks; then merge/push/deploy only on request

---

## Spec coverage checklist

| Spec item | Task |
|---|---|
| Claim embeds envelope | 1 |
| Gateway route + allowlist + renew on gateway | 2 |
| Dedicated renew | 2 |
| store_artifact control-plane root | 2 |
| complete + `remote_container` runtime | 3 |
| Agent opt-in + fail closed + `--network none` | 4 |
| ADR-044 / 0.3.58 / API / handoff | 5 |
| No Alembic | all |
| Non-goals (egress, registry, HQ invent) | not implemented |

## Placeholder / consistency self-review

- Function names locked: `relay_gateway`, `renew_job_lease`, `gateway_remote_job`, `renew_remote_job`
- Runtime string locked: `remote_container`
- Env locked: `FS_CORP_REMOTE_WORKER_RUNTIME=container`
