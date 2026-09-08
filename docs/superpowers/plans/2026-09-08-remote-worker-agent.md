# Remote Worker Pull Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explicit `worker_host_id` enqueues remote jobs; pull agent claims/completes with host token; same-host dispatch unchanged.

**Architecture:** Alembic `0028_remote_worker_jobs`; `company/remote_jobs.py`; extend `dispatch_queued_isolated`; host-token job APIs; `scripts/remote_worker_agent.py`.

**Tech Stack:** Python 3.12+, SQLite, unittest, httpx/urllib for agent.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-08-remote-worker-agent-design.md` (approved).
- No remote Docker; no auto host pick; fail closed.
- Branch: `feature/remote-worker-agent`. Bump to `0.3.56`. Exclude `local repos/service-department/`.

## File map

| Path | Role |
|---|---|
| `alembic/versions/0028_remote_worker_jobs.py` | Migration |
| `company/schema.py` / `migrate.py` | DDL + HEAD |
| `company/remote_jobs.py` | Enqueue/list/claim/complete |
| `company/core.py` | Wrappers + dispatch branch |
| `company/service.py` | HTTP routes |
| `scripts/remote_worker_agent.py` | Pull loop |
| `tests/test_remote_worker_jobs.py` | Coverage |
| Docs | ADR-042, handoff, roadmap |

---

### Task 1: Schema + remote_jobs module

- [ ] Table + HEAD pins → `0028_remote_worker_jobs`
- [ ] `enqueue_remote_job`, `list_host_jobs`, `claim_job`, `complete_job`, lease expiry requeue
- [ ] Tests for claim/complete/fail-closed
- [ ] Commit

### Task 2: Wire dispatch-worker + HTTP

- [ ] `dispatch_queued_isolated(..., worker_host_id=None)` → remote path when set
- [ ] Host-token GET jobs / POST claim / POST complete
- [ ] Tests via TestClient
- [ ] Commit

### Task 3: Agent script + docs

- [ ] `scripts/remote_worker_agent.py`
- [ ] ADR-042, handoff, version `0.3.56`, API contract
- [ ] Full unittest
- [ ] Commit

---

## Spec coverage

| Spec | Task |
|---|---|
| Job table + transitions | 1 |
| Explicit enqueue + APIs | 2 |
| Agent script | 3 |
| ADR / docs | 3 |
