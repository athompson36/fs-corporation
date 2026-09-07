# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **Dispatch options + recommend autofill merged to
`main` (local; ahead of origin; not yet deployed).**

## Dispatch recommend / autofill (merged)

- `GET /api/v1/projects/{id}/dispatch-options` — parameter key (templates, presets, max_cents,
  department status / dispatchable).
- `POST /api/v1/projects/{id}/dispatch-recommend` — advisory mock→live autofill; never dispatches.
  Live uses `invoke_model` when provider status is live; otherwise mock with notes
  (`live_unavailable` / `live_unusable`). ADR-035.
- CEO desk and companion: Recommend button, brief/criteria templates, dept checkboxes + budget
  chips, Valid values panel; dormant checked depts block submit until Activate.

## Prior: Companion iPhone full integration

Scopes are server-derived (`GET /api/v1/session`); paired admin may act as CEO for ops (not root);
five-tab mobile layout. Re-pair phone once after deploy so native session carries scopes.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **351 passed** (post-merge on `main`)
- `cd companion && npm run build`: passed during feature work

## Production feature roadmap (owner-approved 2026-09-07)

Settings **C** (non-secret `FS_CORP_*` editable from Settings; secrets host-only status) + horizon
**everything**. Plan: [docs/superpowers/plans/2026-09-07-production-feature-build-out.md](superpowers/plans/2026-09-07-production-feature-build-out.md).

## Next

1. Optional: `git push origin main` and deploy with `scripts/deploy_to_fs_dev.sh` + remote
   `run-install.sh`.
2. Start **P0.2**: M10-01 idempotency prune, M10-03 model/benchmark read path, replace remaining
   companion `window.prompt` forms; LearningAdapter.fetch; then Settings platform (P1).
3. Do not commit `local repos/service-department/`.
