# Verification record

Updated 2026-09-08 for **0.3.54** (P4 Scale and presence) and Corporate HQ Phases 1–8.
Prior: 0.3.52 runtime department editing; 0.3.51 desk + companion organization/head handoff UI; 0.3.50 local-repos +
Diagnostics; 0.3.49 GitHub assign; 0.3.48 billed
cost/revenue; 0.3.47 companion PWA. Run on Python 3.14.3 in `.venv`
on macOS / Node 18.20.8. CI additionally runs Python 3.12 and 3.13
(`.github/workflows/ci.yml`).

Earlier records: 0.2.0 ZIP (2026-09-01, Python 3.12.13) and 0.3.13 cosmic-glass desk (2026-09-01).

## Verified in this workspace

- **320 unit tests pass** via `.venv/bin/python -m unittest discover -s tests`, including
  persisted-only scorecard periods, zero unrecorded revenue, objective lifecycle/API,
  divisions, staffing, promotion, activity projection, floorplans, worker identity, and prior
  organization behavior.
- `python3 scripts/check_bundle.py` reaches the pre-existing nested local repository and
  fails on `local repos/service-department/README.md` → missing `./LICENSE`; no Task 7
  bundle link/config failure was reported before that point.
- Alembic revision chain is linear and single-headed: `0001_initial` through
  `0023_ceo_scorecard`.
- Companion **0.3.54** build completes (`generateSW`) and emits the production PWA assets.

## Verified on the fs-dev host (owner-operated, not reproducible from CI)

- Live github.com deliveries returning **200** through Tailscale Funnel at
  `https://fs-dev.tail824ab1.ts.net/api/v1/github/webhooks` for `ping`, `push`, and
  `pull_request` on `athompson36/fs-corp-comp`; host recorded `github.webhook_received`.
- Live feed poll and a live pull request from the production-slice exercise.
- Same-host container dispatch with `FS_CORP_DEFAULT_WORKER_RUNTIME=container`.

These depend on owner credentials and physical hardware. They are evidence of a past run,
not a check any clone can repeat.

## Not tested or not implemented

- Real provider invoices / refunds; period rollover of billed totals.
- Live Web Push delivery (needs VAPID keys).
- Phone offline smoke after generateSW.
- Remaining M10-03: benchmark_results / model_profiles consumer or removal; role fixtures.
- Dedicated second worker host; full ChatDev dependency install in the worker image.

## Known drift

- Root / `companion-native` Expo tree may still report transitive `npm audit` findings.
- Without `FS_CORP_MODEL_CENTS_PER_1K_TOKENS` (or profile rate), billed `amount_cents` stays 0
  while `usage_tokens` still records live usage.
- `Company()` now runs Alembic on file-backed databases (0.3.43). Ephemeral `:memory:`
  databases still rely on `apply_schema` alone; that is intentional.
- A locally built `fs-corporation-worker:local` image can predate the current
  `Dockerfile.worker`. Rebuild to pick up labels and entrypoint changes.

Metrics, HQ tiles, and activity badges remain bound to persisted state; no UI surface
invents operational activity. Furnished room art is deferred.
