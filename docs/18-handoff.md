# Current handoff

Date: 2026-09-11. Version: **0.3.69**. State: **Corporate/Workers Browse consistency
merged to `main`, pushed, and deployed to fs-dev** (health `0.3.69`).

## On main / fs-dev

- Corporate Browse lists (packs → activity) use `section-head` + `panel-empty`.
- Workers **Worker hosts** title sits outside the list card (matches Projects/Corporate).
- ADR-051; version **0.3.69**. Projects split (0.3.68) and desk five-domain IA (0.3.67)
  unchanged.
- Tip: `b0aba4b` (includes restore of polish files after a bad handoff commit).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **504 tests passed**.
- fs-dev health: **0.3.69**; companion bundle includes Industry packs / Worker hosts /
  section-head markers.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: Corporate Browse groups/sub-tabs, Org polish, Projects list-row HTML nit,
URL-synced project selection, or other follow-ups.
