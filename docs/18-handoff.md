# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **P0.2 M10 ops merged to `main` (local;
ahead of origin; not yet deployed).**

## P0.2 (merged)

- Idempotency retention default **7 days** (`FS_CORP_IDEMPOTENCY_RETENTION_DAYS`);
  `POST /api/v1/ops/idempotency/prune`.
- `GET /api/v1/model-profiles`, `GET /api/v1/benchmarks`; fixtures in
  `config/benchmarks.example.json`.
- Companion: enroll / escalate / owner-respond are labeled forms (no `window.prompt`).
- `LearningAdapter.fetch` allowlists HTTPS prefixes from
  `config/learning-sources.example.json` (or `FS_CORP_LEARNING_SOURCES_FILE`).

## P1 Settings platform (in progress)

- Companion API client supports GET/PATCH/reset settings and secrets-status.
- Companion Settings now separates Connection, editable Runtime overlays,
  read-only Host values, and configured/missing Secrets without exposing values.
- Runtime entries show their source; restart-gated overlays state that an API
  restart is required.

## Also on main

- Dispatch options + recommend autofill (ADR-035).
- Companion iPhone scopes / paired-admin ops / five-tab layout (ADR-034).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **360 passed** (post-merge)
- Task 4: `cd companion && npm run build`: **passed**.
- Task 4: full unittest discovery: **374 passed, 2 unrelated
  `test_dispatch_recommend` failures** (`live_unavailable` under the current
  environment instead of the tests' expected live-provider paths).

## Production roadmap

Settings **C** + horizon everything:
[docs/superpowers/plans/2026-09-07-production-feature-build-out.md](superpowers/plans/2026-09-07-production-feature-build-out.md).

## Next

1. Optional: `git push origin main` and deploy with `scripts/deploy_to_fs_dev.sh`.
2. Continue **P1 Settings platform** with Task 5 documentation, ADR, and
   capability/roadmap updates.
3. Remaining M10-04 chrome (version in primary UI, HQ tile keyboard) deferred with P5.
4. Do not commit `local repos/service-department/`.
