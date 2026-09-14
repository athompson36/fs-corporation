# Verification record

Updated 2026-09-14 for **0.3.88** (provider invoice headers + allocations onto immutable
`billed_costs`; informational `provider_invoice_variance_cents` on finance summary;
desk `#budget` + companion Finance Browse/Manage provider group; ADR-070; Alembic
**0030_provider_invoices**; no Stripe, no auto-adjustments, no billed mutate).
Prior headline 0.3.61 retained below as historical host evidence.

## Verified in this workspace (0.3.88)

- **600 unit tests pass** via `.venv/bin/python -m unittest discover -s tests`.
- Provider invoice contracts: `tests/test_provider_invoices.py`,
  `tests/test_desk_provider_invoices.py`.
- Alembic head **0030_provider_invoices** (linear single head).
- Companion version lockstep **0.3.88**; `cd companion && npm run build` when shipping.

Updated 2026-09-14 for **0.3.87** (consultant work-order baseline/after ops measurements;
GET measurements list + detail with arithmetic deltas; desk `#consultant` + companion
Home Needs-you; ADR-069; Alembic **0029_work_order_measurements**; no invented scores).

## Verified in this workspace (0.3.87)

- **595 unit tests pass** via `.venv/bin/python -m unittest discover -s tests`.
- Measurement contracts: `tests/test_work_order_measurements.py`,
  `tests/test_desk_consultant_measurements.py`.
- Alembic head **0029_work_order_measurements** (linear single head).
- Companion version lockstep **0.3.87**; `cd companion && npm run build` when shipping.

Updated 2026-09-14 for **0.3.86** (finance open-next budget period after close; pricing
honesty on finance summary; desk + companion Open next + hint; ADR-068; no auto-rollover).

## Verified in this workspace (0.3.86)

- **587 unit tests pass** via `.venv/bin/python -m unittest discover -s tests`.
- Finance contracts: `tests/test_durable_finance.py`, `tests/test_desk_finance_open_next.py`.
- Desk session gates: prior Finance/Org/corporate gate modules unchanged.
- Companion version lockstep **0.3.86**; `cd companion && npm run build` when shipping.
- No Alembic revision in 0.3.86.

Updated 2026-09-14 for **0.3.85** (desk remaining session gates: Org write on
Activate/promotions/staffing; `project.enroll` on dispatch submit/recommend; docs honesty).

## Verified in this workspace (0.3.85)

- **576 unit tests pass** via `.venv/bin/python -m unittest discover -s tests`.
- Desk contracts: `tests/test_desk_remaining_session_gates.py` plus prior Finance/Org/corporate gate modules.
- Companion version lockstep **0.3.85**; `cd companion && npm run build` when shipping.
- No Alembic revision in 0.3.85.

Updated 2026-09-08 for **0.3.61** (remote ChatDev egress policy on claims; opt-in auto remote
placement; public `/welcome`; marketing `campaign` furniture; remote container-on-agent; P5; P4)
and Corporate HQ Phases 1–8.
Prior: 0.3.58 remote container-on-agent; 0.3.52 runtime department editing; 0.3.51 desk + companion organization/head handoff UI; 0.3.50 local-repos +
Diagnostics; 0.3.49 GitHub assign; 0.3.48 billed
cost/revenue; 0.3.47 companion PWA. Run on Python 3.14.3 in `.venv`
on macOS / Node 18.20.8. CI additionally runs Python 3.12 and 3.13
(`.github/workflows/ci.yml`).

Earlier records: 0.2.0 ZIP (2026-09-01, Python 3.12.13) and 0.3.13 cosmic-glass desk (2026-09-01).

## Verified in this workspace

- **471 unit tests pass** via `.venv/bin/python -m unittest discover -s tests`, including
  claim egress policy/coercion, allowlisted-network agent readiness, fail-closed unready egress,
  mock egress isolation, opt-in auto remote placement, public `/welcome` content and Caddy
  routing, remote claim envelopes, host-token gateway allowlisting and prior behavior.
- `python3 scripts/check_bundle.py` reaches the pre-existing nested local repository and
  fails on `local repos/service-department/README.md` → missing `./LICENSE`; no Task 7
  bundle link/config failure was reported before that point.
- Alembic revision chain is linear and single-headed: `0001_initial` through
  `0028_remote_worker_jobs`; 0.3.61 adds no migration.
- Companion **0.3.61** build completes (`generateSW`) and emits the production PWA assets.

## Verified on the fs-dev host (owner-operated, not reproducible from CI)

- Live github.com deliveries returning **200** through Tailscale Funnel at
  `https://fs-dev.tail824ab1.ts.net/api/v1/github/webhooks` for `ping`, `push`, and
  `pull_request` on `athompson36/fs-corp-comp`; host recorded `github.webhook_received`.
- Live feed poll and a live pull request from the production-slice exercise.
- Same-host container dispatch with `FS_CORP_DEFAULT_WORKER_RUNTIME=container`.

These depend on owner credentials and physical hardware. They are evidence of a past run,
not a check any clone can repeat.

## Not tested or not implemented

- Real provider invoices / refunds.
- Live Web Push delivery (needs VAPID keys).
- Phone offline smoke after generateSW.
- Remaining M10-03: benchmark_results / model_profiles consumer or removal; role fixtures.
- Live remote container execution on a dedicated second host; full ChatDev dependency install
  in the worker image.

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
