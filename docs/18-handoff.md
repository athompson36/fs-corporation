# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **HQ Phase 1–8 APIs wired to desk + companion UI**.

## UI wiring verification

Corporate HQ endpoints are tied to operator surfaces:

- **CEO desk** (`company/service.py`): default floorplan, create position, reorder departments,
  cross-department create/list/accept (`pending_acceptance`), staffing scan + decide, promotion
  approve/reject, plus existing scorecard/objectives/HQ/activity/packs/divisions
- **Companion PWA** (`companion/src/`): Org tab gains create position, reorder, worker card lookup;
  new **Corporate** tab covers scorecard, objectives, packs/divisions, promotions, staffing,
  cross-department requests, activity, and default floorplan
- **companion-native**: WebView of the companion PWA — no separate route surface required
- Regression: `tests.test_companion_api.CompanionApiTests.test_desk_and_companion_wire_hq_phase_surfaces`

Not every internal API is a companion control (task dispatch internals, learning certify, feed
poll, remote-access pairing on desk, etc.). Those remain desk/API-only or diagnostics probes by
design.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **321 passed**
- `cd companion && npm run build`: passed

## Next

Resume M10-03 with a benchmark-results/model-profile read path or removal, preserving the
persisted-evidence rule and existing governance boundaries. Commit the UI wiring when ready.
