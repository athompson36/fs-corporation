# Current handoff

Date: 2026-09-07. Version: **0.3.45**. State: **M10-01 complete** (worker-completion transaction).

## Delivered in 0.3.45

- `Company.mark_worker_completed` finishes the worker run, marks the queue `done`, and emits
  `task.worker_completed` in one transaction.
- Subprocess and container runtimes both call it; failure path still uses `_finish_worker_run`.
- Test: `test_mark_worker_completed_rolls_back_together_on_failure` in `tests/test_workers.py`.

## M10-01 series (0.3.42–0.3.45)

| Version | Item |
|---------|------|
| 0.3.42 | HTTP 429 rate limiting |
| 0.3.43 | Alembic on startup |
| 0.3.44 | Atomic idempotency |
| 0.3.45 | Worker-completion transaction |

## Verify

```bash
.venv/bin/python -m unittest tests.test_workers -v
.venv/bin/python -m unittest discover -s tests
python3 scripts/check_bundle.py
```

## Next implementation

**M10-02 test gaps**, in order:

1. Adapter `cancel` / `fail` mapping tests
2. Consultant stale-evidence rejection test
3. Non-loopback bind refusal test
4. SSE stream test

Before the next fs-dev companion rebuild: **M10-04** hanging `vite-plugin-pwa` service-worker
build (`npm run build` never exits; `dist/sw.js` never emitted).
