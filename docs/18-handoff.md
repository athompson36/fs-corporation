# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **P0.2 M10 ops on `feature/p0-m10-ops`
(ready to merge): idempotency prune, model/benchmark reads, companion forms, learning fetch.**

## P0.2 on this branch

- Idempotency retention default **7 days** (`FS_CORP_IDEMPOTENCY_RETENTION_DAYS`);
  `POST /api/v1/ops/idempotency/prune`.
- `GET /api/v1/model-profiles`, `GET /api/v1/benchmarks`; fixtures in
  `config/benchmarks.example.json`.
- Companion: enroll / escalate / owner-respond are labeled forms (no `window.prompt`).
- `LearningAdapter.fetch` allowlists HTTPS prefixes from
  `config/learning-sources.example.json` (or `FS_CORP_LEARNING_SOURCES_FILE`).
- Plan: [docs/superpowers/plans/2026-09-07-p0-m10-ops.md](superpowers/plans/2026-09-07-p0-m10-ops.md).

## Already on main

- Dispatch options + recommend autofill (ADR-035).
- Companion iPhone scopes / paired-admin ops / five-tab layout (ADR-034).

## Verification

- Run `.venv/bin/python -m unittest discover -s tests` and `cd companion && npm run build`
  before merge.

## Production roadmap

Settings **C** + horizon everything:
[docs/superpowers/plans/2026-09-07-production-feature-build-out.md](superpowers/plans/2026-09-07-production-feature-build-out.md).

## Next

1. Merge `feature/p0-m10-ops` → `main`; optional push/deploy.
2. Start **P1 Settings platform** (spec/plan for GET/PATCH settings + secrets-status).
3. Remaining M10-04 chrome (version in primary UI, HQ tile keyboard) deferred with P5.
4. Do not commit `local repos/service-department/`.
