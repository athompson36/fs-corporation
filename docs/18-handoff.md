# Current handoff

Date: 2026-09-07. Version: **0.3.50**. State: **local repo candidates + Diagnostics**.

## Delivered in 0.3.50

- `GET /api/v1/local-repos` scans `local repos/` (or `FS_CORP_LOCAL_REPOS_DIR`)
- Desk + companion: Local candidates with Enroll; Diagnostics probes status endpoints +
  local-repos (unavailable on failure, no invented state)
- Companion package **0.3.50**

## Prior

- 0.3.49 GitHub assign-by-address; 0.3.48 billed/revenue; 0.3.47 PWA generateSW

## Verify

```bash
.venv/bin/python -m unittest tests.test_local_repos -v
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
python3 scripts/check_bundle.py
```

## Next implementation

Deploy 0.3.50 to fs-dev. Remaining M10-04: version in primary chrome, HQ keyboard,
replace remaining `window.prompt` flows.
