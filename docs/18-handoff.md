# Current handoff

Date: 2026-09-11. Version: **0.3.68**. State: **Projects Browse split polish merged to
`main`, pushed, and deployed to fs-dev** (health `0.3.68`).

## On main / fs-dev

- Companion Projects **Browse** is a responsive list|detail split (`project-browse-split`);
  detail is the full project workspace (brief, GitHub, dispatch); **Clear selection**
  replaces ← Back; Manage remains enroll/assign.
- Medium empty/section polish on Corporate, Workers, Org. Finance still has no
  Browse/Manage ModeSwitch.
- ADR-050; version **0.3.68** (Python + companion lockstep). Desk five-domain IA from
  0.3.67 unchanged.
- Tip: `09a5aa8`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **501 tests passed**.
- fs-dev health: **0.3.68**; companion bundle includes `project-browse-split`,
  `Select a project`, `Clear selection`.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: further Corporate/Workers hierarchy polish, URL-synced project selection,
or other companion/desk follow-ups from prior reviews.
