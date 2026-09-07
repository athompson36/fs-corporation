# Current handoff

Date: 2026-09-07. Version: **0.3.42**. State: **HTTP 429 rate limiting** delivered; M10-01 continues.

## Delivered in 0.3.42

- Per-principal sliding-window rate limit on authenticated `/api/v1/*` (default 120/60s).
- Per-IP limit on `POST /api/v1/github/webhooks` and `POST /api/v1/remote-access/redeem` (default 60/60s).
- Exempt: `GET /`, `GET /desk`, `GET /api/v1/health` — never return 429.
- Over-limit responses include `Retry-After`. Configurable via `FS_CORP_RATE_LIMIT_AUTH`,
  `FS_CORP_RATE_LIMIT_UNAUTH`, `FS_CORP_RATE_LIMIT_WINDOW_SEC`; tests inject via
  `create_app(..., rate_limit=...)`.
- Module: `company/rate_limit.py`. Tests: `tests/test_rate_limit.py`.

## Prior (0.3.41 audit)

Hermetic tests, secrets script fix, honest docs, M10 backlog, ADRs 021–024, rebuilt worker image.

## Verify

```bash
.venv/bin/python -m unittest tests.test_rate_limit tests.test_api -v
env -i PATH="$PATH" HOME="$HOME" .venv/bin/python -m unittest discover -s tests
python3 scripts/check_bundle.py
```

## Next implementation

**M10-01 remaining**, in order:

1. Alembic on startup or explicit drift detection (`Company()` / `apply_schema` cannot ALTER).
2. Atomic idempotency — `remember_command` must commit with the protected effect.
3. Worker-completion transaction gap in `company/worker.py`.

Then M10-02 test gaps. Before the next fs-dev companion rebuild: M10-04 hanging
`vite-plugin-pwa` service-worker build.
