# Design: Finance Browse/Manage + URL sync

Date: 2026-09-12. Status: **approved design (pending implementation as v0.3.77)**.

## Goal

Give companion **Money / Finance** the same Browse/Manage ModeSwitch and hybrid
`ManageClusters` chrome as Work/People panels: lists vs create forms, with
deep-linkable `mode` / `group` query params — without new finance APIs or
changing money math.

## Owner locks

| Topic | Choice |
|---|---|
| Split | Lists vs forms — Browse holds lists/overview; Manage holds create forms |
| Close period | Stays Browse in-row action on Periods list |
| URL | Full — `tab=finance` participates in App `mode` + `group` sync |
| Chrome | Reuse `ManageClusters` hybrid (wide labeled scroll; narrow segmented tabs) |
| Approach | Extend App URL + controlled `FinancePanel` (same pattern as 0.3.76) |

## Non-goals

- New finance APIs, Alembic, or money-rule changes (ADR-038 math unchanged).
- Desk Finance surface; PDF / Stripe / payment rails.
- `pushState` Back stacks.
- Changing Work/People panel memberships beyond making `finance` mode-capable.

## Browse groups (`mode` omitted or `browse`)

| `group` id | Content |
|---|---|
| `overview` | Summary card (gross / adjustments / net / revenue / open period). **Default** — omit from URL. |
| `invoices` | Invoice list; expand loads line detail |
| `adjustments` | Adjustment list |
| `periods` | Period list; **Close period** in-row when `canPause` |

## Manage groups (`mode=manage`)

| `group` id | Content |
|---|---|
| `invoice` | Create invoice form. **Default** — omit from URL. |
| `adjustment` | Post adjustment form |
| `period` | Set budget period form |

`canPause` false: Manage still reachable but forms replaced by existing
`scopeNotice(...)` (same strings as today). No invented totals.

## URL rules (extend ADR-058)

1. Add `finance` to `MODE_CAPABLE_TABS`.
2. For `tab=finance` only: serialize `group` in **both** Browse and Manage
   (omit when equal to that mode’s default). Other mode-capable tabs keep
   writing `group` only when Manage.
3. Parse: validate finance `group` against the active mode’s allowed set;
   invalid → that mode’s default.
4. Leaving Finance or switching mode resets `group` to the new mode’s default
   (same tab-change / mode-change reset pattern as other panels).
5. Pairing `#fs-pair=` and `project` rules unchanged. History remains
   `replaceState` only.

Examples:

- `/?tab=finance` → Browse Overview
- `/?tab=finance&group=periods` → Browse Periods
- `/?tab=finance&mode=manage` → Manage Create invoice
- `/?tab=finance&mode=manage&group=adjustment` → Manage Post adjustment

## UI

- Top: `ModeSwitch` (`label="Finance mode"`).
- Remove the old flat Overview · Invoices · Adjustments · Periods segmented bar.
- Remove lede copy that says create actions are “not a second Browse/Manage
  layer”; replace with a short lede consistent with other panels.
- Browse and Manage each render one `ManageClusters` (or equivalent shared
  chrome) with the group tables above.
- Prefer section-head / `panel-empty` consistency with sibling panels where
  lists are empty.

## State ownership

- App owns `panelMode` and `manageGroup` (URL `group`) when `tab=finance`,
  same as other mode-capable tabs.
- `FinancePanel` becomes controlled: `mode`, `onModeChange`, `group`,
  `onGroupChange` (or reuse `manageGroup` / `onManageGroupChange` naming for
  consistency with Org/Projects/Workers).
- No finance-local ModeSwitch-only state after this release.

## Delivery

| Path | Role |
|---|---|
| `companion/src/urlState.ts` | `finance` mode-capable; finance browse+manage group tables |
| `companion/src/App.tsx` | Wire FinancePanel controlled props; reset rules |
| `companion/src/FinancePanel.tsx` | ModeSwitch + ManageClusters split |
| `tests/test_*` | Source contracts for markers + version **0.3.77** |
| Docs | UX, ADR-059, roadmap, handoff; mark this spec implemented |

## Verification

- Source contracts: ModeSwitch + ManageClusters in FinancePanel; finance group
  ids in urlState; App wires props; version **0.3.77**.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: Browse lists; Close period; Manage forms; deep links refresh;
  `!canPause` notices; Work/People URL sync unaffected.

## Follow-ups (deferred)

- One-frame tab-change URL flash (0.3.76 nit).
- Behavioral (non-source) URL helper tests.
- Desk Finance surface.
