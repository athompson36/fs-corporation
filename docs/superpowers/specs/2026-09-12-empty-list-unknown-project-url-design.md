# Design: Empty-list unknown-project URL clear

Date: 2026-09-12. Status: **implemented in v0.3.75**.

## Goal

Close the companion URL-sync edge where a stale `?project=` survives when the
enrolled projects list is loaded and empty — without clearing valid deep links
before the first successful projects fetch, and without toasts or new APIs.

## Owner locks

| Topic | Choice |
|---|---|
| When list is “available” | After first **successful** projects refresh (`projectsLoaded`) |
| Failed first fetch | Leave `projectsLoaded` false; keep `?project=` until a later success |
| Unknown / empty-list clear | Silent `setSelectedProject(null)`; existing replaceState drops `project` |
| Approach | Boolean `projectsLoaded` (not `projects: null \| array`) |

## Non-goals

- Manage/Browse mode in the URL.
- Corporate / Manage cluster URL sync.
- Finance ModeSwitch.
- Error toasts for unknown project ids.
- New APIs, Alembic, desk/welcome changes.
- Changing `parseCompanionSearch` / `serializeCompanionSearch` semantics beyond
  contracts that assert the loaded-gate in `App.tsx`.

## Problem

ADR-055 required: after the enrolled `projects` list is available, clear
`selectedProject` when the id is not in the list (drop `project` from the URL;
keep `tab`; no toast).

Current clear effect:

```ts
if (!selectedProject || !projects.length) return;
```

That early return treats **loaded-empty** the same as **not loaded yet**, so
`?tab=projects&project=stale` never clears when enroll is empty.

## Behavior

1. Add `projectsLoaded` state, default `false`.
2. On successful refresh path that calls `setProjects(...)`, also
   `setProjectsLoaded(true)`.
3. On refresh failure (`catch` / offline): do **not** set `projectsLoaded`; leave
   any boot/`popstate` `selectedProject` intact.
4. Replace the clear effect with:

   ```ts
   if (!projectsLoaded || !selectedProject) return;
   const known = projects.some((p) => String(p.id) === selectedProject);
   if (!known) setSelectedProject(null);
   ```

   Empty `projects` after a successful load → unknown → clear.
5. Existing serialize + `replaceState` effect continues to omit `project` when
   selection is null.
6. Leaving Projects still clears selection as today.

## Delivery

| Path | Role |
|---|---|
| `companion/src/App.tsx` | `projectsLoaded`; set on success; gate unknown clear |
| `tests/test_companion_url_sync.py` (or sibling) | Assert loaded-gate markers; no `!projects.length` early-return on clear |
| Docs | UX brief, ADR-057, roadmap, handoff; version **0.3.75** |

## Verification

- Source contracts: `projectsLoaded` / `setProjectsLoaded(true)` on success path;
  clear effect gated on `projectsLoaded` (not `!projects.length` alone); version
  **0.3.75**.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: boot with `?tab=projects&project=<unknown>` after empty enroll →
  selection/URL clear after successful refresh; valid deep link still works when
  id is enrolled; failed refresh does not clear.

## Follow-ups (deferred)

- Manage/Browse URL sync.
- Finance ModeSwitch.
- Abort in-flight `api.project` on Clear (prior nit).
