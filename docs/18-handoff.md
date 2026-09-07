# Current handoff

Date: 2026-09-07. Version: **0.3.49**. State: **phone GitHub assign-by-address shipped**.

## Delivered in 0.3.49

- `POST /api/v1/projects/{id}/github-assign`: paste upstream URL/`owner/repo`, ensure
  same-owner `{repo}-corp`, enroll both numeric ids
- Companion Projects form (admin): Assign GitHub — no `window.prompt` for this path
- `companion-admin-*` may enroll/dispatch/github (CEO mobile); App installation account
  must match upstream owner
- Companion package **0.3.49**

## Prior

- 0.3.48 billed cost/revenue; 0.3.47 PWA generateSW; 0.3.46 M10-02

## Verify

```bash
.venv/bin/python -m unittest tests.test_github_assign tests.test_companion_api -v
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
python3 scripts/check_bundle.py
```

## Next implementation

Deploy 0.3.49 to fs-dev for phone smoke. Remaining M10-03 benchmarks / M10-04 UI
(version display, status surface, keyboard, replace remaining prompts).
