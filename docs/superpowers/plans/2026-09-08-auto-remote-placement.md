# Auto Remote Placement Implementation Plan

> **For agentic workers:** Use executing-plans / implement task-by-task.

**Goal:** Opt-in prefer ready remotes when `worker_host_id` omitted; fail closed if none ready.

**Tech:** Settings catalog + placement helper in `company/remote_jobs.py` or `company/worker_placement.py`; wire `dispatch-worker`.

## Tasks

1. Catalog key + `choose_remote_host(company) -> id | None`
2. Wire dispatch path; return `placement` in enqueue result
3. Tests + ADR-043 + bump `0.3.57` + handoff next → A
