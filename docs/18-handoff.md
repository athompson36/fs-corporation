# Current handoff

Date: 2026-09-07. Version: **0.3.44**. State: **Atomic idempotency** delivered; M10-01 nearly done.

## Delivered in 0.3.44

- `Company.tx()` is re-entrant so nested domain mutations join an outer transaction.
- `Company.run_idempotent` runs the handler and inserts `command_idempotency` in one commit.
- API `run()` uses `run_idempotent` whenever an `Idempotency-Key` is present, so a crash can
  no longer leave an applied effect without a replayable record (or the reverse).
- Tests: `tests/test_idempotency_atomic.py`.

## Prior

- 0.3.43 Alembic on startup for file-backed DBs
- 0.3.42 HTTP 429 rate limiting
- 0.3.41 same-host worker plane + audit remediation

## Verify

```bash
.venv/bin/python -m unittest tests.test_idempotency_atomic tests.test_api -v
.venv/bin/python -m unittest discover -s tests
python3 scripts/check_bundle.py
```

## Next implementation

**M10-01 last item:** worker-completion transaction — `company/worker.py` updates the queue
and emits `task.worker_completed` outside `tx()`.

Then M10-02 test gaps. Before the next fs-dev companion rebuild: M10-04 hanging
`vite-plugin-pwa` service-worker build.
