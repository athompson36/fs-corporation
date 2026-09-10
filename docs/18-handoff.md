# Current handoff

Date: 2026-09-10. Version: **0.3.65**. State: **Companion shell + CEO spine merged to
`main`, pushed, and deployed to fs-dev** (health `0.3.65`).

## On main / fs-dev

- Companion primary navigation is **Home · Work · People · Money · More**. Work groups
  Projects/Corporate/Workers; People opens Organization; Money opens Finance; More retains
  Decisions/Inbox/Diagnostics/Settings.
- Home is a Needs-you queue from persisted decisions and owner-inbox only (inline
  approve/reject/respond; escalate create stays in More → Inbox).
- Shared Syne/Manrope via `/static/brand-fonts.css` and cosmic-glass font tokens across
  companion, desk, and welcome.
- ADR-047; no Alembic (head unchanged). Merge commit on `main`: `a5253fb` (+ follow-up
  hardenings already on the merged branch tip before merge).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **484 tests passed**.
- `cd companion && npm run build`: **OK**.
- fs-dev health: **0.3.65**; `/`, `/welcome`, `/desk`, `/static/brand-fonts.css`, and
  Syne/Manrope woff2 assets **200**; companion bundle includes Needs-you / Work chrome.
- Do not commit `local repos/service-department/`.

## Next

Owner-directed: **deep layout polish inside Work/People/Money** or **desk information
architecture alignment to the five companion domains**.
