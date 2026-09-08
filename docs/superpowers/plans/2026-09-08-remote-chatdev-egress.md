# Remote ChatDev Egress Implementation Plan

Status: **implemented** in v0.3.61.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed company ChatDev egress policy on remote job claim; remote container agents use allowlisted Docker networks only when locally ready, otherwise fail the job.

**Architecture:** `claim_job` adds an `egress` object (`mode`, `docker_network`) derived from company settings with coerce for forbidden network names. The remote agent extends `build_docker_cmd` / readiness checks; mock path ignores egress. No Alembic.

**Tech Stack:** Existing `company.chatdev_egress`, `company.remote_jobs`, `scripts/remote_worker_agent.py`, unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-08-remote-chatdev-egress-design.md`
- Version **0.3.61**; ADR-046; no Alembic (HEAD `0028_remote_worker_jobs`)
- Never send allowlist hostnames on the wire
- Never use Docker `bridge`/`host`; coerce those at claim to `mode=none`
- Allowlist + agent unready → `complete` failed (no silent `--network none`)
- Branch: `feature/remote-chatdev-egress` from `main`
- Do not commit `local repos/service-department/`

## File map

| File | Responsibility |
|---|---|
| `company/chatdev_egress.py` or `company/remote_jobs.py` | `claim_egress_policy(company) -> dict` |
| `company/remote_jobs.py` | Attach `egress` on `claim_job` |
| `scripts/remote_worker_agent.py` | Network selection + local readiness for allowlist |
| `tests/test_remote_container_agent.py` / new helpers | Claim + agent tests |
| Docs / version | ADR-046, 0.3.61, API, handoff → P3 finance |

---

### Task 1: `claim_egress_policy` + claim response

**Files:**
- Modify: `company/chatdev_egress.py` (preferred) or `company/remote_jobs.py`
- Modify: `company/remote_jobs.py` `claim_job`
- Test: `tests/test_remote_container_agent.py` (or `tests/test_remote_chatdev_egress.py`)

**Interfaces:**
- Produces: `claim_egress_policy(company) -> {"mode": "none"|"allowlist", "docker_network": str|None}`
- Never includes host lists

- [x] **Step 1: Write failing tests**

```python
from company.chatdev_egress import claim_egress_policy
from company.remote_jobs import claim_job, enqueue_remote_job
# setup host+task as in existing remote tests

def test_claim_includes_egress_none_by_default(self):
    ...
    claimed = claim_job(...)
    self.assertEqual(claimed["egress"]["mode"], "none")
    self.assertIsNone(claimed["egress"]["docker_network"])

def test_claim_egress_allowlist_when_configured(self):
    # set company overlay or env FS_CORP_CHATDEV_WORKER_EGRESS=allowlist
    # and FS_CORP_CHATDEV_EGRESS_DOCKER_NETWORK=fs-corp-chatdev
    ...
    self.assertEqual(claimed["egress"]["mode"], "allowlist")
    self.assertEqual(claimed["egress"]["docker_network"], "fs-corp-chatdev")

def test_claim_coerces_bridge_to_none(self):
    # mode allowlist + network bridge → mode none, docker_network null
    ...
```

- [x] **Step 2: Run — expect FAIL** (missing `egress` / function)

- [x] **Step 3: Implement**

```python
FORBIDDEN_NETWORKS = frozenset({"", "bridge", "host"})

def claim_egress_policy(company) -> dict:
    mode = egress_mode(company)
    if mode != "allowlist":
        return {"mode": "none", "docker_network": None}
    network = (docker_network_name() or "").strip()
    if network.lower() in FORBIDDEN_NETWORKS or not network:
        return {"mode": "none", "docker_network": None}
    return {"mode": "allowlist", "docker_network": network}
```

In `claim_job`, after envelope:

```python
from company.chatdev_egress import claim_egress_policy
out["egress"] = claim_egress_policy(company)
```

Use existing settings overlay helpers if tests need `FS_CORP_CHATDEV_WORKER_EGRESS` without process-wide env pollution where possible; env is OK if cleaned up in `addCleanup`.

- [x] **Step 4: PASS focused tests**

- [x] **Step 5: Commit** when appropriate

---

### Task 2: Agent network selection + fail-closed allowlist

**Files:**
- Modify: `scripts/remote_worker_agent.py`
- Modify: `tests/test_remote_container_agent.py`

**Interfaces:**
- `build_docker_cmd(docker, image, scratch, network: str = "none") -> list[str]`
- `agent_egress_ready(policy: dict) -> tuple[bool, str]` — False + reason if allowlist unmet
- `execute_claimed_job` / `once`: read `claimed["egress"]`; if allowlist and not ready → failed complete; else pass network into `build_docker_cmd`

- [x] **Step 1: Failing tests**

```python
def test_build_docker_cmd_allowlist_network(self):
    cmd = build_docker_cmd("docker", "img", Path("/tmp/x"), network="fs-corp-chatdev")
    self.assertIn("--network", cmd)
    self.assertIn("fs-corp-chatdev", cmd)
    self.assertNotIn("none", cmd[cmd.index("--network")+1])  # careful: only that slot

def test_agent_egress_ready_false_without_allowlist_file(self):
    ok, reason = agent_egress_ready({"mode": "allowlist", "docker_network": "net"})
    self.assertFalse(ok)

def test_once_allowlist_unready_fails_without_mock(self):
    # similar to missing docker test: complete status failed, type remote_egress_unready
```

- [x] **Step 2: Run — FAIL**

- [x] **Step 3: Implement**

```python
def agent_egress_ready(policy: dict) -> tuple[bool, str]:
    if (policy or {}).get("mode") != "allowlist":
        return True, ""
    network = str(policy.get("docker_network") or "").strip()
    if not network or network.lower() in {"bridge", "host"}:
        return False, "egress docker_network missing or forbidden"
    # Reuse chatdev_egress.load_https_hosts / allowlist_path if importable from agent
    # Prefer importing company.chatdev_egress (agent already may import company for nothing —
    # today agent is stdlib-only). Keep agent stdlib-only: duplicate minimal checks OR
    # allow importing company.chatdev_egress (package is installed on agent hosts that run
    # the script from the repo). Spec: agent has allowlist file via env.
    try:
        from company.chatdev_egress import allowlist_path, load_https_hosts
        path = allowlist_path()
        if path is None:
            return False, "egress allowlist file not configured"
        hosts = load_https_hosts(path)
        if not hosts:
            return False, "egress allowlist empty"
    except Exception as exc:
        return False, f"egress allowlist unready: {exc}"
    # Network existence: `docker network inspect <name>` 
    ...
    return True, ""

def build_docker_cmd(..., network: str = "none"):
    net = (network or "none").strip() or "none"
    if net.lower() in {"bridge", "host"}:
        net = "none"
    return [..., "--network", net, ...]
```

Wire `once` / `execute_claimed_job` to use policy from claim.

**Import note:** Prefer importing `company.chatdev_egress` from the agent (repo-installed) rather than vendoring allowlist logic. If import fails, treat allowlist as unready.

- [x] **Step 4: PASS** focused agent tests

- [x] **Step 5: Commit**

---

### Task 3: Docs, ADR-046, version 0.3.61

**Files:**
- Version bump: `company/__init__.py`, `companion/package.json`, `README.md`, `VERIFICATION.md`
- `docs/decisions.md` ADR-046
- `docs/16-api-contract.md` — claim returns `egress`
- `docs/18-handoff.md`, `docs/14-roadmap.md` — next → P3 finance
- Spec status → implemented; commit plan+spec

ADR-046 summary:
> Remote claim embeds ChatDev egress policy; agents attach allowlisted Docker networks only when locally ready; forbidden names coerced to none at claim; no hostnames on the wire.

- [x] **Step 1: Docs/version**
- [x] **Step 2: Full suite** `.venv/bin/python -m unittest discover -s tests`
- [x] **Step 3: Companion build** for version bump
- [x] **Step 4: Commit** when owner asks; merge/push/deploy only on request

---

## Spec coverage

| Spec item | Task |
|---|---|
| Claim `egress` object | 1 |
| Coerce bridge/host/empty | 1 |
| Agent allowlist ready path | 2 |
| Agent fail closed | 2 |
| Mock ignores egress | 2 |
| ADR-046 / 0.3.61 / handoff → finance | 3 |
| No hostnames / no Alembic | all |

## Self-review

- Function names: `claim_egress_policy`, `agent_egress_ready`
- Failure type string locked for tests: prefer `remote_egress_unready`
- Version `0.3.61`; ADR `046`
