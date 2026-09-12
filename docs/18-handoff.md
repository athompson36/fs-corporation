# Current handoff

Date: 2026-09-12. Version: **0.3.76**. State: **Mode/cluster/group URL sync
merged to `main`, pushed, and deployed to fs-dev.** Tip: **`7acef49`**.

## On main / fs-dev

- `companion/src/urlState.ts` — parse/serialize `mode`/`cluster`/`group`; omit
  defaults; validate ids per tab.
- `companion/src/App.tsx` — App-owned `panelMode`, `corporateCluster`,
  `manageGroup`; replaceState + popstate; Workers token → `group=token`;
  read-only Org/Corporate clamps.
- `companion/src/{Org,Corporate,Projects,Workers}Panel.tsx` — controlled mode,
  cluster (Corporate), manage group props.
- `companion/src/ManageClusters.tsx` — optional controlled `activeGroupId`.
- `tests/test_mode_cluster_group_url_sync.py` — contracts; exact version
  **0.3.76**.
- ADR-058; version **0.3.76** (Python package and companion `package.json`
  lockstep).
- Prior: empty-list unknown-project URL clear (0.3.75), Manage visual groups
  (0.3.74), Companion URL sync (0.3.73).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **529 tests, OK**.
- `cd companion && npm run build`: OK (package version 0.3.76).
- fs-dev: `GET /api/v1/health` → `{"ok":true,"version":"0.3.76",...}`; companion
  bundle rebuilt (`index-C2rFawQr.js`).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: Finance ModeSwitch; or other companion/desk follow-ups.
