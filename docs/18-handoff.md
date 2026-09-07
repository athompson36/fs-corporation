# Current handoff

Date: 2026-09-07. Version: **0.3.43**. State: **Alembic on startup** delivered; M10-01 continues.

## Delivered in 0.3.43

- File-backed `Company()` runs `alembic upgrade head` after `apply_schema`, so column-only
  migrations (e.g. `0011_pairing_access_level`) apply even when the DB was created by an older
  app build. Fails closed if still behind head.
- `:memory:` databases skip Alembic (in-repo SCHEMA is complete for ephemeral use).
- Per-path lock + fast path when already at `HEAD_REVISION` so concurrent `Company(path)`
  openers do not deadlock SQLite.
- Module: `company/migrate.py`. Tests: `tests/test_migrate.py`.

## Prior (0.3.42)

HTTP 429 rate limiting per principal / IP; health and desk exempt.

## Verify

```bash
.venv/bin/python -m unittest tests.test_migrate tests.test_core.PersistenceTests -v
.venv/bin/python -m unittest discover -s tests
python3 scripts/check_bundle.py
```

## Next implementation

**M10-01 remaining**, in order:

1. Atomic idempotency — `remember_command` must commit with the protected effect.
2. Worker-completion transaction gap in `company/worker.py`.

Then M10-02 test gaps. Before the next fs-dev companion rebuild: M10-04 hanging
`vite-plugin-pwa` service-worker build.
