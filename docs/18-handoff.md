# Current handoff

Date: 2026-09-12. Version: **0.3.76**. State: **Mode/cluster/group URL sync on
branch `feature/mode-cluster-group-url-sync` (pending merge/deploy).** Tip:
**`4e82a61`**.

## On feature branch

- `companion/src/urlState.ts` — parse/serialize `mode`/`cluster`/`group`; omit
  defaults; validate ids per tab.
- `companion/src/App.tsx` — App-owned `panelMode`, `corporateCluster`,
  `manageGroup`; replaceState + popstate; Workers token → `group=token`.
- `companion/src/{Org,Corporate,Projects,Workers}Panel.tsx` — controlled mode,
  cluster (Corporate), manage group props.
- `companion/src/ManageClusters.tsx` — optional controlled `activeGroupId`.
- `tests/test_mode_cluster_group_url_sync.py` — contracts; exact version
  **0.3.76**.
- `tests/test_companion_url_sync.py` — tab/project contracts; soft version pin.
- ADR-058; version **0.3.76** (Python package and companion `package.json`
  lockstep).
- Prior: empty-list unknown-project URL clear (0.3.75), Manage visual groups
  (0.3.74), Companion URL sync (0.3.73).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **529 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.76).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: merge/deploy 0.3.76; Finance ModeSwitch; or other
companion/desk follow-ups.
