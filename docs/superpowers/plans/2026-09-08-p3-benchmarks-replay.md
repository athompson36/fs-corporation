# P3 Follow-on: Benchmarks + Work-order Replay Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prefer best benchmark quality in `choose_model` among eligible profiles; add append-only work-order replay ledger.

**Architecture:** Extend `company/routing.py`; Alembic `0026_work_order_replays`; Company + consultant wire-in; read API for replays.

**Tech Stack:** Python 3.12+, SQLite, unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-08-p3-benchmarks-replay-design.md`.
- No invented benchmarks; no ChatDev re-execution.
- Branch: `feature/p3-benchmarks-replay`.

---

### Task 1: choose_model quality preference

- [ ] Tests in `tests/test_routing_benchmarks.py`
- [ ] Implement in `company/routing.py`
- [ ] Commit

### Task 2: Replay ledger table + core

- [ ] Schema + alembic `0026` + HEAD_REVISION
- [ ] `record_work_order_authorized`, `complete_work_order_outcome`, `replay_work_order`, `list_work_order_replays`
- [ ] Wire `to_work_order`
- [ ] HTTP GET replays
- [ ] Tests + commit

### Task 3: Docs + handoff + ADR-039

- [ ] Docs; handoff next → P4
- [ ] Commit
