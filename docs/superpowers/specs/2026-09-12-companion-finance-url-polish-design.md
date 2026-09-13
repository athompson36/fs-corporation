# Design: Companion finance URL polish (0.3.79)

Date: 2026-09-12. Status: **approved for implementation** (target **v0.3.79**).

## Goal

Close three deferred companion nits from Finance Browse/Manage and URL sync
reviews: dead Close-period focus, mode-aware cold-load/popstate group fallback,
and a minimal behavioral harness for `urlState` parse/serialize.

## Owner locks

| Topic | Choice |
|---|---|
| Track | Companion polish batch (not desk polish) |
| Depth | Two code fixes + Node/tsx behavioral URL harness |
| Harness | `companion/scripts/check-url-state.mts` via `npx --yes tsx` from Python |
| Version | **0.3.79** |

## Non-goals

- Desk Finance pause gate / openRoom spend display.
- One-frame tab-change URL flash.
- Vitest or new permanent companion test-runner dependency.
- New finance APIs, ModeSwitch redesign, Alembic.

## Fix 1 — Dead Close-period focus

In `FinancePanel.closePeriod` (Browse in-row):

- **Keep** prefill of period start from closed `period_end` (state still used when
  user opens Manage → Period).
- **Remove** `window.setTimeout(() => periodStartRef.current?.focus(), 0)` —
  Manage period input is not mounted in Browse.
- **Remove** `onManageGroupChange("periods")` — Close already runs on Browse
  Periods; the call was a no-op / leftover from pre-ModeSwitch layout.

If `periodStartRef` becomes unused after removing focus, remove the ref as well.

## Fix 2 — Cold-load / popstate `defaultGroupFor`

In `App.tsx`:

- Initial `manageGroup` state: when `initialUrl.group` is null, use
  `defaultGroupFor(initialUrl.tab, initialUrl.mode)` (not `defaultManageGroup`).
- `popstate` handler: same — `parsed.group ?? defaultGroupFor(parsed.tab, parsed.mode)`.
- Keep `"catalog"` (or existing) ultimate string fallback only where today’s code
  already has a non-null assert pattern; prefer `?? defaultGroupFor(...) ?? "catalog"`
  for non-finance tabs that still need a string.

Finance Browse cold load without `group` must land on **overview**, not manage’s
**invoice**.

## Behavioral URL harness

| Path | Role |
|---|---|
| `companion/scripts/check-url-state.mts` | Import parse/serialize from `../src/urlState.ts`; run fixed assertions; exit 1 on failure |
| `tests/test_url_state_behavior.py` | `subprocess` → `npx --yes tsx companion/scripts/check-url-state.mts` from repo root |
| Source contracts (same or sibling test module) | App init/popstate use `defaultGroupFor`; FinancePanel `closePeriod` lacks focus / post-close `onManageGroupChange("periods")`; version **0.3.79** |

Minimum harness cases:

1. Finance browse defaults → search omits `mode`/`group` (e.g. `?tab=finance` or empty extras).
2. Finance browse `group=periods` round-trips.
3. Finance manage default omits `group` (keeps `mode=manage`).
4. Finance manage `group=adjustment` round-trips.
5. Invalid finance browse group coerces to overview on parse.
6. Projects manage default omits `group`.
7. For each fixture string: `serialize(parse(s))` equals the canonical serialized form.

No new `package.json` dependency; `npx --yes tsx` is acceptable for this offline
starter’s local/CI node. If `node`/`npx` missing, the Python test fails with a
clear message (do not silently skip — this repo’s unittest gate should catch
missing tooling when node is expected for companion).

## Delivery

| Path | Role |
|---|---|
| `companion/src/FinancePanel.tsx` | Fix 1 |
| `companion/src/App.tsx` | Fix 2 |
| `companion/scripts/check-url-state.mts` | Harness |
| `tests/test_*` | Behavior + source contracts; soften prior exact `0.3.78` pins |
| Docs | ADR-061, UX/roadmap/handoff; mark this spec implemented when shipped |
| Versions | `company/__init__.py` + `companion/package.json` → **0.3.79** |

Branch: `feature/companion-finance-url-polish`.

## Verification

- Harness exits 0; unittest discover green; `cd companion && npm run build`.
- Manual: Close period stays on Browse Periods; `/?tab=finance` shows Overview;
  `/?tab=finance&mode=manage` shows Create invoice (not a browse group id).

## Follow-ups (deferred)

- Desk pause-gate / openRoom display polish.
- One-frame tab-change URL flash.
- Broader Vitest suite (if later desired).
