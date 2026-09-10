# Current handoff

Date: 2026-09-10. Version: **0.3.65**. State: **Companion shell + CEO spine
implemented on `feature/companion-shell-ceo-spine`; not yet merged or deployed.**

## Implemented on the feature branch

- Companion primary navigation is **Home · Work · People · Money · More**. Work groups
  Projects/Corporate/Workers; People opens Organization; Money opens Finance; More retains
  Decisions/Inbox/Diagnostics/Settings.
- Home is a Needs-you queue built only from persisted pending decisions and owner-inbox
  requests. Existing scope-gated approve/reject/respond actions are reused; escalation
  creation stays in More → Inbox.
- Shared self-hosted Syne/Manrope font CSS and cosmic-glass font tokens align companion,
  desk and welcome without changing APIs, the desk IA or the welcome hero.
- Versions are 0.3.65. ADR-047 and the companion/UX/roadmap/spec documentation record the
  release. No Alembic revision is required.
- Changed release files: `company/__init__.py`, `companion/package.json`,
  `tests/test_companion_api.py`, `docs/11-user-experience.md`,
  `docs/14-roadmap.md`, `docs/18-handoff.md`, `docs/24-mobile-companion.md`,
  `docs/decisions.md`, and the companion shell design/plan under `docs/superpowers/`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **484 tests passed**.
- `cd companion && npm run build`: **OK** (Vite leaves `/static/fonts/...` URLs for
  runtime resolution, as intended for same-origin serving).
- The first full-suite run found a stale Finance source assertion from the old tab model;
  it now checks the Money primary sentinel while retaining the `tab === "finance"` and
  `FinancePanel` assertions.
- No fs-dev deploy or post-deploy route/font smoke check was performed for 0.3.65.
- Do not commit `local repos/service-department/`.

## Next

Choose either **deep layout polish inside Work/People/Money** or **desk information
architecture alignment to the five companion domains**. After merge/deploy, verify fs-dev
health reports 0.3.65 and smoke-test `/`, `/desk`, `/welcome`, and shared font assets.
