# Design: URL-synced companion tab + project selection

Date: 2026-09-12. Status: **implemented in v0.3.73**.

## Goal

Deep-link the companion with shareable `?tab=` and `?project=` query params so
refresh/bookmark restores the active tab and Projects selection — without React
Router, Browse/Manage in the URL, or new APIs.

## Owner locks

| Topic | Choice |
|---|---|
| Scope | Full deep link — `tab` + `project` |
| History | Replace — `history.replaceState` on every tab/project change |
| Unknown project | Clear selection; keep `tab`; drop `project`; no toast |
| Delivery | Small URL helpers + effects in `App.tsx` |

## Non-goals

- Browse/Manage mode in the URL.
- Corporate cluster (or other panel-local state) in the URL.
- React Router / new routing dependency.
- `pushState` Back stacks.
- New APIs, Alembic, Manage visual groups, desk/welcome changes.
- Changing list-row / Clear-on-loading UX beyond wiring selection to the URL.

## URL shape

Pathname unchanged. Hash remains reserved for `#fs-pair=`.

| Param | Values | Rules |
|---|---|---|
| `tab` | Existing `Tab` ids (`dashboard`, `projects`, `organization`, `corporate`, `workers`, `decisions`, `inbox`, `diagnostics`, `finance`, `settings`) | Always written when known. Invalid/missing on boot → `dashboard`. |
| `project` | Project id string | Present only when `tab=projects` and a selection exists. Omitted when selection is null, tab ≠ `projects`, or id is unknown after projects load. |

Example: `/?tab=projects&project=alpha`.

## Boot

1. Parse `window.location.search` once (before/alongside initial state).
2. If `tab` is a valid `Tab`, use it; else `dashboard`.
3. If `project` is non-empty, set `selectedProject` and ensure tab is `projects`
   (even if `tab` was missing/invalid) so the deep link opens Work → Projects.
4. Do not clear `#fs-pair=` until existing redeem/`clearPairingHash` runs.

## Writes

Whenever `tab` or `selectedProject` changes, build the canonical query and call
`history.replaceState(null, "", pathname + search)` (preserve hash only if it
is not a pairing hash being cleared by existing logic; after pairing clear,
search may remain).

- Leaving Projects or Clear selection → omit `project`.
- Leaving Projects also clears `selectedProject` so stale detail fetches do not
  continue off-tab. Non-`projects` tabs never write `project` into the URL.

## Unknown project

After the enrolled `projects` list is available: if `selectedProject` is set and
not found in that list → `setSelectedProject(null)` and rewrite URL without
`project` (keep `tab`). No error toast.

## Pairing

Existing `#fs-pair=` redeem and `clearPairingHash()` stay as today (strip hash,
keep pathname + search). Query sync must not strip the pair hash before redeem.

## popstate

Re-parse search on `popstate` and apply the same boot rules (replace-only means
Back usually leaves the app; re-parse still helps if the browser fires it).

## Delivery

| Path | Role |
|---|---|
| `companion/src/App.tsx` | Parse/serialize helpers; boot; replaceState effect; unknown-project clear; popstate |
| Optional: `companion/src/urlState.ts` | Pure parse/serialize if it keeps `App.tsx` smaller |
| `tests/test_companion_url_sync.py` | Source contracts on helpers + App markers |
| Docs | UX brief, ADR-055, roadmap, handoff; version **0.3.73** |

Prefer extracting pure `parseCompanionSearch` / `serializeCompanionSearch` (or
equivalent) so unittest can lock behavior without a browser.

## Verification

- Source tests: valid/invalid tab; project forces projects tab; serialize omits
  project off Projects; unknown-id clear markers; `#fs-pair` helpers preserved;
  version **0.3.73**.
- `.venv/bin/python -m unittest discover -s tests`
- `cd companion && npm run build`
- Manual: open `/?tab=projects&project=<id>`; refresh; Clear; switch tab; pair
  QR still works; bad project id clears silently.

## Follow-ups (deferred)

- Manage visual groups.
- URL sync for Browse/Manage or Corporate clusters.
- Abort/guard in-flight `api.project` when clearing mid-load.
