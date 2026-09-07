# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **P1 Settings platform slice A done on
`feature/settings-platform-p1` (local; not merged to `main`).**

## P0.2 (merged)

- Idempotency retention default **7 days** (`FS_CORP_IDEMPOTENCY_RETENTION_DAYS`);
  `POST /api/v1/ops/idempotency/prune`.
- `GET /api/v1/model-profiles`, `GET /api/v1/benchmarks`; fixtures in
  `config/benchmarks.example.json`.
- Companion: enroll / escalate / owner-respond are labeled forms (no `window.prompt`).
- `LearningAdapter.fetch` allowlists HTTPS prefixes from
  `config/learning-sources.example.json` (or `FS_CORP_LEARNING_SOURCES_FILE`).

## P1 Settings platform slice A (done)

- `company_settings` SQLite overlay + catalog (`company/settings_catalog.py`,
  `company/settings_runtime.py`); effective resolution overlay → env → default.
- APIs: `GET/PATCH /api/v1/settings`, `POST /api/v1/settings/reset`,
  `GET /api/v1/settings/secrets-status` (ADR-036).
- Hot-apply wired for non-`restart_required` keys; rate-limit keys store overlay but
  take effect only after API restart (`restart_required: true`, honest UI copy).
- Companion Settings: Connection, editable **Runtime** (source badge + restart notice),
  read-only **Host**, configured/missing **Secrets** (no values).
- Tests: `tests/test_settings_platform.py`, companion API/build coverage.

## Also on main

- Dispatch options + recommend autofill (ADR-035).
- Companion iPhone scopes / paired-admin ops / five-tab layout (ADR-034).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **382 passed** (2026-09-07).
- `cd companion && npm run build`: **passed** (2026-09-07).

## Final branch review fixes

- Restored the local/default worker runtime to `subprocess`; fs-dev remains explicitly
  configured for `container`.
- Rate-limit overlays now seed the policy on app startup; these settings remain
  restart-required.
- Public URL validation requires HTTPS with a host and rejects userinfo/fragments.
- Settings listing falls back per invalid item instead of failing the entire request.
- ChatDev status no longer implies an overlay controls the isolated-worker gate.
- Reset-all deletes editable overlays only.

## Production roadmap

Settings **C** slice A complete; slice B (desk mirror + expanded sections) or **P2 Live ops**
next: [docs/superpowers/plans/2026-09-07-production-feature-build-out.md](superpowers/plans/2026-09-07-production-feature-build-out.md).

## Next

1. Merge `feature/settings-platform-p1` to `main`; optional deploy with
   `scripts/deploy_to_fs_dev.sh`.
2. **P2 Live ops completeness** (feeds CRUD, push/GitHub secret-status polish, ChatDev egress)
   **or** expand Settings sections (Company, Models, Workers, …) — owner choice.
3. Desk Settings UI deferred (companion-only in slice A).
4. Remaining M10-04 chrome (version in primary UI, HQ tile keyboard) deferred with P5.
5. Do not commit `local repos/service-department/`.
