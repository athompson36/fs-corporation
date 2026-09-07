# Current handoff

Date: 2026-09-07. Version: **0.3.46**. State: **M10-02 complete** (test gaps closed).

## Delivered in 0.3.46

- `MockChatDevAdapter.cancel` / `.fail` contract assertions in `tests/test_m2.py`
- Consultant stale-evidence refusal in `tests/test_consultant.py`
- Non-loopback bind refusal via subprocess in `tests/test_service_edges.py`
- SSE stream cursor frames (`{seq, kind, at}`) in `tests/test_service_edges.py`
- `FS_CORP_SSE_IDLE_SEC` (default `1`; `0` ends after one page so tests do not hang)

## Prior M10-01 (0.3.42–0.3.45)

429 → Alembic-on-startup → atomic idempotency → worker-completion transaction.

## Verify

```bash
.venv/bin/python -m unittest tests.test_service_edges tests.test_m2 tests.test_consultant -v
.venv/bin/python -m unittest discover -s tests
python3 scripts/check_bundle.py
```

## Next implementation

Prefer **M10-04 hanging companion PWA build** before any fs-dev install that rebuilds the
companion (`vite-plugin-pwa` hangs on `src/sw.ts`; `dist/sw.js` never emitted).

Otherwise **M10-03** financial model (billed cost / revenue tables) or M10-04 UI items
(status surface, version display, desk keyboard access, `window.prompt` replacement).
