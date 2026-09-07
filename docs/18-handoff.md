# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **Dispatch options + recommend autofill implemented on
`feature/dispatch-recommend-autofill` (not yet merged to main / not yet deployed).**

## Dispatch recommend / autofill (this branch)

- `GET /api/v1/projects/{id}/dispatch-options` — parameter key (templates, presets, max_cents,
  department status / dispatchable).
- `POST /api/v1/projects/{id}/dispatch-recommend` — advisory mock→live autofill; never dispatches.
  Live uses `invoke_model` when provider status is live; otherwise mock with notes
  (`live_unavailable` / `live_unusable`). ADR-035.
- CEO desk and companion: Recommend button, brief/criteria templates, dept checkboxes + budget
  chips, Valid values panel; dormant checked depts block submit until Activate.

## Prior: Companion iPhone full integration (main)

Scopes are server-derived (`GET /api/v1/session`); paired admin may act as CEO for ops (not root);
five-tab mobile layout. Re-pair phone once after deploy so native session carries scopes.

## Verification (this branch)

- `.venv/bin/python -m unittest discover -s tests` — run before merge
- `cd companion && npm run build` — passed during Task 4
- Focused: `tests.test_dispatch_recommend`, `tests.test_companion_api` — OK

## Production feature roadmap (owner-approved 2026-09-07)

Settings **C** (non-secret `FS_CORP_*` editable from Settings; secrets host-only status) + horizon
**everything**. Plan: [docs/superpowers/plans/2026-09-07-production-feature-build-out.md](superpowers/plans/2026-09-07-production-feature-build-out.md).

## Next

1. Merge `feature/dispatch-recommend-autofill` (finishing options: PR vs local merge) and deploy
   when ready.
2. Start **P0.2 / P1**: M10-01 idempotency prune, M10-03 model/benchmark read path, replace remaining
   companion `window.prompt` forms; then Settings platform spec/plan.
3. Do not commit `local repos/service-department/`.
