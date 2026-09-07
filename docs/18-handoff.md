# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **Corporate HQ Phases 1–8 complete on `feature/corporate-hq-phases`**.

## Corporate HQ Phase 8

- Alembic `0023_ceo_scorecard` adds governed objectives and optional immutable scorecard
  snapshots; in-memory schema and startup migration head match
- CEO/admin companions create and close objectives; title, timezone-aware due date, optional
  division, and JSON target persist with lifecycle events
- scorecard computation reads persisted acceptance events, QC inspections, dispatches,
  reservations/ledger, billed costs, and revenue only
- period bounds are half-open (`period_start <= timestamp < period_end`); accepted tasks are
  deduplicated by persisted task id; absent revenue remains zero and absent QC is unmeasured
- Desk renders the six metrics, objective list, create control, and close controls under the
  label “Measured from persisted operations — not simulated.”
- authenticated endpoints: `GET /api/v1/scorecard`, `GET/POST /api/v1/objectives`, and
  `POST /api/v1/objectives/{id}/close`

Changed implementation: `company/core.py`, `company/schema.py`, `company/migrate.py`,
`company/service.py`, `alembic/versions/0023_ceo_scorecard.py`, and
`tests/test_scorecard.py`. Migration-head assertions in the Phase 5–7 regression tests now
track `0023_ceo_scorecard`. Version metadata is 0.3.53 in Python and the companion package.
README, data model, organization note, roadmap, decision log, verification record, and this
handoff describe the delivered behavior.

## Corporate HQ completion

1. runtime department/position editing
2. persisted floorplans, rooms, and requirement warnings
3. validated worker sprites, identity, and joined worker cards
4. transactional event-projected live activity
5. evidence-backed career ladders and promotions
6. approval-gated staffing proposals and atomic hires
7. governed divisions and persisted industry packs
8. persisted-data CEO scorecard and objective lifecycle

## Verification

- `.venv/bin/python -m unittest tests.test_scorecard -v`: **5 passed**
- `.venv/bin/python -m unittest discover -s tests`: **320 passed**
- `PYTHONPATH=. .venv/bin/alembic heads`: **0023_ceo_scorecard (head)**
- `cd companion && npm run build`: passed; Vite transformed 32 modules and generated the PWA
- IDE diagnostics: no errors in changed Python files
- `scripts/check_bundle.py`: still blocked by the pre-existing untracked
  `local repos/service-department/README.md` link to missing `./LICENSE`; Phase 8 did not
  modify or commit that unrelated local repository tree

## Next

Resume M10-03 with a benchmark-results/model-profile read path or removal, preserving the
persisted-evidence rule and existing governance boundaries.
