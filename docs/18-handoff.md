# Current handoff

Date: 2026-09-01. Version: 0.3.4. State: loopback control service plus local M1–M7 control-plane behavior. Subprocess-isolated workers dispatch queued mock work through a parent-mediated gateway. Hired employees have regular documented training, performance goals/reviews/trends, and configurable backgrounds. Quality Control still gates acceptance. Live adapters remain disabled.

## Delivered

- Nested M0–M7 checklists in docs/14-roadmap.md. ADR-010–014: loopback stack, hardware skills, QC/HR, employee development, isolated workers.
- Shared schema and Alembic revisions through `0005_worker_runs`.
- Bearer-token identities; `/api/v1` on loopback; policy, delegations, consultant, GitHub denials, impact briefs, CEO desk.
- Hardware skill gaps; Quality Control inspection before acceptance.
- Human Resources: hire with attributes/background, pertinent training cycle, reviewable training files, performance goals, reviews and trends. Overdue training blocks hired-employee dispatch.
- Isolated workers: `SubprocessWorkerRuntime` with gateway allowlist; `POST /api/v1/tasks/{task_id}/dispatch-worker`; `worker_runs` audit. Container runtime fail-closed.

## Verification

Unit tests pass under `.venv` after `pip install -e .` (Python 3.14 in this workspace; CI matrix remains 3.12/3.13): **67 tests**, including `tests/test_workers.py`. The standard-library demo still runs without FastAPI. `python3 scripts/check_bundle.py` passed. Remote GitHub CI has not run.

## Limitations that must remain visible

The loopback service is not a sandbox against someone with the SQLite file or Python process. Subprocess workers reduce accidental DB exposure but are not a malicious-code sandbox. Container worker image is not built. No actual model calls, GitHub writes, feed retrieval, billed spend, webhooks, isometric art, or live documentation fetch. Training uses supplied HTTPS metadata. Performance scores are recorded integers, not live evaluations. Demo actor `head` is not a hired employee and is not blocked by the training cycle. Live adapters still raise NotImplementedError. SLOs are unmeasured. Owner tokens live in `.local/owner.token`.

## Next task

Supply GitHub App installation + disposable repo IDs, one enabled text-model credential for use only inside the worker/gateway boundary, and optionally one approved feed or documentation source list. Build a container worker image and wire live ChatDev through the gateway. Do not bind off loopback or skip denial tests.

## Missing live configuration

Selected GitHub repository/fork IDs and App installation; exact enabled provider/model IDs and credentials; actual spending caps; approved sources/watchlists (including hardware documentation); deployment target; desired final company name and visual style; Docker worker image build pipeline. Do not infer these from unrelated user history.

## Context continuity

Preserve all fourteen user requirements in docs/00-project-context.md, including employee development (requirement 14 / R21). New user steering updates that file, relevant acceptance criteria and this handoff. Do not reduce the project to a generic chatbot, code-only agency or decorative office simulation.

## Commands

```bash
python3 -m company demo
python3 -m unittest discover -s tests -v   # needs pip install -e . for API tests
python3 -m company.service --host 127.0.0.1 --port 8000
python3 -m company backup --dest .local/company.backup.db
```
