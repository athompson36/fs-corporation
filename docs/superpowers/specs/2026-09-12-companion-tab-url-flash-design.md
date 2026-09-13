# Design: Companion tab/mode URL flash fix (0.3.81)

Date: 2026-09-12. Status: **implemented in v0.3.81**.

## Goal

Eliminate the one-frame wrong companion search string when switching **tabs** or
**Browse/Manage mode**. Address bar must never show a transient non-canonical
`mode` / `cluster` / `group` for those transitions. Prefer one batched React
update so panel chrome and URL stay aligned.

## Owner locks

| Topic | Choice |
|---|---|
| Success | Address bar never shows a transient wrong `mode`/`cluster`/`group` on tab/mode change |
| Scope | Tab + mode change; leave permission-clamp timing alone unless a flash appears |
| Approach | Batch sibling resets with `selectTab` / `handlePanelModeChange` (not smart URL writer, not deferred replaceState) |
| Proof | Extend tsx `urlState` harness for transition sequences + thin Python source contracts |
| Version | **0.3.81** |

## Non-goals

- Rewrite org/corporate permission clamp effects unless a flash is observed.
- React Router, `pushState` Back stacks, or pairing-hash changes.
- Desk changes, FinancePanel behavior, Vitest, Alembic, new APIs.

## Problem

`App.tsx` writes canonical search via a `replaceState` effect over
`tab` / `panelMode` / `corporateCluster` / `manageGroup`. Separate effects reset
siblings **after** tab or mode changes. Effect order means the URL writer can run
once with the **new** tab or mode and **stale** siblings (classic case: leave
Organization Manage → Finance briefly shows `?tab=finance&mode=manage` before
browse defaults). `serializeCompanionSearch` coerces invalid groups but does
**not** strip a stale `mode=manage` on a newly selected tab.

## Behavior

### Tab change (`selectTab`)

In one batched update:

1. `setTab(next)`
2. `setPanelMode("browse")`
3. `setCorporateCluster("strategy")`
4. `setManageGroup(defaultGroupFor(next, "browse") ?? defaultGroupFor(next, "manage") ?? "catalog")`
5. Existing project-clear rules remain (non-projects clears `selectedProject` via
   today’s effect or equivalent in the same batch if already co-located)

Update `tabRef` (and `modeRef` when mode is forced to browse) in the same
handler path used today for popstate safety so a following effect does not
re-reset.

Wire **all** user tab navigations through `selectTab` (bottom bar, Work/More
segmented controls, dashboard open-decisions/inbox, etc.). Do not call raw
`setTab` for those paths.

### Mode change (`handlePanelModeChange`)

In one batched update (after existing corporate `!canManageOrg` manage block):

1. `setPanelMode(mode)`
2. Group reset matching today’s mode-effect:
   - If `tab === "finance"`: always
     `setManageGroup(defaultGroupFor("finance", mode) ?? "overview")`.
   - Else if tab is mode-capable and `mode === "manage"`:
     `setManageGroup(defaultGroupFor(tab, "manage") ?? "catalog")`.
   - Else: leave `manageGroup` unchanged (non-finance browse).

Update `modeRef` in the handler the same way popstate does.

### URL writer

Keep a single dumb `replaceState` effect over App-owned state. After batched
setters, one render → one canonical write. No write-time “detect lag and invent
defaults” logic.

### Effects to remove or shrink

- Tab-change reset effect (`tabRef` + set browse/strategy/group) — superseded by
  `selectTab`; keep popstate updating `tabRef` before `setTab`.
- Mode-change reset effect (`modeRef` + set group) — superseded by
  `handlePanelModeChange`; keep popstate updating `modeRef`.
- Leave org/corporate permission clamp effects as-is unless verification shows a
  flash.

### popstate

Unchanged contract: parse search → set refs then state (tab, project, mode,
cluster, group) together so batched handlers are not required for history
traversal. Do not run `selectTab` on popstate (would force browse and fight the
URL).

## Pure helpers (`urlState.ts`)

Export small pure helpers used by App and the harness, for example:

- `stateAfterTabChange(prev, nextTab)` → next `CompanionUrlState` with browse,
  strategy, default group, project cleared when leaving projects.
- `stateAfterModeChange(prev, nextMode)` → next state with mode + default group
  per rules above (no-op / browse force when tab not mode-capable).

Exact names may vary; behavior must match the harness cases below.

## Harness cases (extend `check-url-state.mts`)

Simulate transitions by applying helpers then `serializeCompanionSearch`. Assert
**each** step’s serialized search equals the canonical end state (no intermediate
string that includes stale manage mode or wrong group).

Minimum cases:

1. Organization Manage (default group) → Finance → `?tab=finance` (no `mode`).
2. Finance Manage → Dashboard → `?tab=dashboard`.
3. Corporate Browse `cluster=people` → Organization → `?tab=organization` (no
   `cluster`).
4. Finance Browse `group=periods` → Manage → `?tab=finance&mode=manage` (group
   default omitted).
5. Finance Manage `group=adjustment` → Browse → `?tab=finance`.
6. Existing parse/serialize fixtures remain green.

Python: existing `tests/test_url_state_behavior.py` keeps driving the harness.
Add/adjust source contracts: `selectTab` / batched mode handler; removed
tab/mode reset effects (or equivalent proof they no longer set state after URL
write); version **0.3.81**. Soften any exact `0.3.80` companion pins.

## Delivery

| Path | Role |
|---|---|
| `companion/src/urlState.ts` | Transition helpers |
| `companion/src/App.tsx` | `selectTab`; extend `handlePanelModeChange`; wire call sites; drop redundant reset effects |
| `companion/scripts/check-url-state.mts` | Transition sequence assertions |
| `tests/test_*` | Harness + source contracts |
| Docs | ADR-063, UX/roadmap/handoff; mark this spec implemented when shipped |
| Versions | `company/__init__.py` + `companion/package.json` → **0.3.81** |

Branch: `feature/companion-tab-url-flash`.

## Verification

- Harness exits 0; unittest discover green; `cd companion && npm run build`.
- Manual: from Organization Manage switch to Finance — address bar must not
  flash `mode=manage`; ModeSwitch must land on Browse without a Manage blink.
- Manual: Finance Browse Periods → Manage — lands on Create invoice URL/UI
  without a wrong `group` flash.

## Follow-ups (deferred)

- Init-time Desk Finance disable before session.
- Permission-clamp URL timing (only if a flash is found).
- Broader Vitest suite (if later desired).
