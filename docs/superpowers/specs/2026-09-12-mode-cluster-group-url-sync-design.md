# Design: Manage/Browse + cluster/group URL sync

Date: 2026-09-12. Status: **approved design (pending implementation as v0.3.76)**.

## Goal

Deep-link companion Browse/Manage mode, Corporate Browse clusters, and Manage
visual groups with shareable query params — without React Router, pushState Back
stacks, Finance ModeSwitch, or new APIs.

## Owner locks

| Topic | Choice |
|---|---|
| Scope | Browse/Manage + Manage visual groups + Corporate Browse clusters |
| History | `replaceState` only (match `tab`/`project`) |
| Param shape | Shared short names: `mode`, `cluster`, `group` |
| State ownership | Lift to `App`; panels controlled |
| Approach | Extend `urlState.ts` + one App writer |

## Non-goals

- Finance ModeSwitch / nested Money Browse/Manage.
- React Router or other routing libraries.
- `pushState` history stacks for mode/cluster/group flips.
- Desk/welcome changes.
- New APIs or Alembic revisions.
- Changing pairing `#fs-pair=` behavior.

## URL shape

Pathname unchanged. Hash remains reserved for `#fs-pair=`.

Existing params (`tab`, `project`) keep ADR-055 / ADR-057 rules.

| Param | Values | Rules |
|---|---|---|
| `mode` | `browse` \| `manage` | Written only when `tab` ∈ {`projects`, `organization`, `corporate`, `workers`}. **Omit when `browse`** (default). Invalid/missing → `browse`. |
| `cluster` | `strategy` \| `structure` \| `people` \| `coordination` | Written only when `tab=corporate` and effective mode is Browse. **Omit when `strategy`** (default). Invalid → `strategy`. |
| `group` | Tab-specific Manage ids (below) | Written only when effective mode is Manage on a mode-capable tab. **Omit when that tab’s default group**. Invalid for active tab → that tab’s default. |

Examples:

- `/?tab=corporate&mode=manage&group=ops`
- `/?tab=corporate&cluster=people` (Browse; `mode` omitted)
- `/?tab=projects&mode=manage&group=github&project=alpha`
- `/?tab=organization` (Browse Catalog defaults; no extra params)

### Manage `group` ids by tab

| Tab | Valid `group` | Default |
|---|---|---|
| `organization` | `catalog`, `seats`, `positions`, `lookup` | `catalog` (or `lookup` when `!canManage` — see below) |
| `corporate` | `goals`, `structure`, `coordination`, `ops` | `goals` |
| `projects` | `enroll`, `github` | `enroll` |
| `workers` | `hosts`, `token` | `hosts` |

`cluster=structure` (Corporate Browse) and `group=structure` (Corporate Manage) are
different params; they do not collide.

### Scope / canManage

When Organization cannot Manage (`!canManage`), App still allows `mode=manage` in
the URL only if the panel exposes Manage (Lookup-only chrome). Prefer: if the
panel renders Manage with Lookup-only groups, default `group=lookup` and accept
only `lookup` as valid; unknown groups → `lookup`. If Manage UI is hidden
entirely for the actor, force effective mode to `browse` and drop `mode`/`group`
from writes (match today’s “Manage gated by canManage” for Corporate/Org forms).

Workers: after host create, continue forcing the Token group (today’s remount /
`defaultGroupId` behavior) by setting App `manageGroup` to `token` when a
one-time token is issued.

## Boot / popstate

1. Parse `tab` / `project` as today.
2. Parse `mode` / `cluster` / `group` with the tables above relative to
   resolved `tab`.
3. If `mode=manage` but `tab` is not mode-capable → ignore `mode`/`group`/`cluster`.
4. If `cluster` present with non-corporate tab or Manage mode → ignore `cluster`.
5. If `group` present with Browse (or non-capable tab) → ignore `group`.
6. Re-parse on `popstate` the same way.

## Writes

Whenever `tab`, `selectedProject`, `panelMode`, `corporateCluster`, or
`manageGroup` changes, serialize canonical search and `history.replaceState`.

- Leaving a mode-capable tab → clear App panel-mode state to defaults and omit
  `mode` / `cluster` / `group`.
- Switching to Browse → omit `group`; keep or default `cluster` only on Corporate.
- Switching to Manage → omit `cluster`; write `group` only if not default.
- `project` rules unchanged; may coexist with `mode`/`group` on Projects.

## Delivery

| Path | Role |
|---|---|
| `companion/src/urlState.ts` | Parse/serialize + validation helpers for mode/cluster/group |
| `companion/src/App.tsx` | Own state; replaceState effect; pass controlled props |
| `companion/src/OrgPanel.tsx` | Controlled mode + manage group |
| `companion/src/CorporatePanel.tsx` | Controlled mode + cluster + manage group |
| `companion/src/ProjectsPanel.tsx` | Controlled mode + manage group |
| `companion/src/WorkersPanel.tsx` | Controlled mode + manage group; token forces `token` |
| `companion/src/ManageClusters.tsx` | Optional controlled `activeGroupId` / `onActiveGroupIdChange` |
| `tests/test_companion_url_sync.py` (and/or sibling) | Source contracts |
| Docs | UX, ADR-058, roadmap, handoff; version **0.3.76** |

Prefer pure helpers in `urlState.ts` so unittest can lock serialize/parse without a
browser.

## Verification

- Source tests: omit defaults; validate ids per tab; ignore stale cluster/group;
  App wires controlled props; version **0.3.76**.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: deep-link Corporate Manage Ops; Corporate Browse People; Org Manage
  Seats; Workers Token after create; refresh restores; Clear/project rules intact;
  pairing hash still works.

## Follow-ups (deferred)

- Finance ModeSwitch.
- `pushState` Back stacks.
- Abort in-flight `api.project` on Clear.
