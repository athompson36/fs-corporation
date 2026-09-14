# Design: Desk Finance init-time mutate disable (0.3.82)

Date: 2026-09-14. Status: **approved for planning** (owner locks below).

## Goal

Close the 0.3.80 review nit: Finance mutate controls must not appear enabled
before `/api/v1/session` scopes are known. Fail closed from first paint through
session apply.

## Owner locks

| Topic | Choice |
|---|---|
| Depth | Both HTML `disabled` on static mutate controls **and** JS `setFinanceMutateEnabled(false)` at init |
| Notice | `#finance-scope-notice` visible from markup (no `hidden`) until session enables mutations |
| Session / 403 | Unchanged (`applyFinancePauseFromSession` in `load()`; 403 fail-closed backup) |
| Version | **0.3.82** |

## Non-goals

- New finance APIs, Alembic, or companion FinancePanel behavior beyond version lockstep.
- Desk ModeSwitch / ManageClusters.
- Broader desk session-cache refactor beyond Finance init disable.
- Separate “checking permissions…” copy (owner chose reuse of pause notice).

## Problem

After 0.3.80, mutate controls are enabled in markup and only gated late in
`load()` via `applyFinancePauseFromSession()`. Until that await completes (and
before JS runs), submit/helper chips look clickable. Close-period buttons are
created later and inherit session state when rendered.

## Behavior

1. **Markup**
   - `#finance-scope-notice`: remove `hidden` so it is visible on first paint.
   - Add `disabled` to:
     - `desk-finance-invoice-submit`
     - `desk-finance-adjustment-submit`
     - `desk-finance-period-submit`
     - `desk-finance-invoice-month`
     - `desk-finance-period-30d`
2. **Init:** Immediately after `setFinanceMutateEnabled` is defined, call
   `setFinanceMutateEnabled(false)` once (notice stays visible; any helper-managed
   control stays disabled).
3. **Unchanged:** `await applyFinancePauseFromSession()` before `loadFinance()`;
   `postFinanceCommand` 403 → `setFinanceMutateEnabled(false)`.
4. Owner with `company.pause` may briefly see the pause notice, then controls
   enable and notice hides when session succeeds.

## Delivery

| Path | Role |
|---|---|
| `company/service.py` | DESK_HTML markup + init call |
| `tests/test_desk_finance_init_disable.py` | Source contracts + version **0.3.82** |
| Soften | Any exact `0.3.81` pins that fail after lockstep bump → `0\.3\.\d+` where appropriate |
| Docs | ADR-064, UX/roadmap/handoff; mark this spec implemented when shipped |
| Versions | `company/__init__.py` + `companion/package.json` → **0.3.82** |

Branch: `feature/desk-finance-init-disable`.

## Verification

- Source contracts: notice markup lacks `hidden`; five controls have `disabled`;
  init `setFinanceMutateEnabled(false)` present; `/api/v1/session` + 403 path
  still present; version **0.3.82**.
- Full `unittest discover`; `cd companion && npm run build`.
- Manual: cold desk load → Finance chips disabled + pause notice visible until
  session; owner token → enable + notice hidden; missing pause / session error →
  stay disabled.

## Follow-ups (deferred)

- Permission-clamp companion URL timing (only if a flash is found).
- Broader desk use of `/api/v1/session` for other mutate UIs.
