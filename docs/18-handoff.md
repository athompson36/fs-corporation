# Current handoff

Date: 2026-09-11. Version: **0.3.67**. State: **desk five-domain IA implemented locally**
on `feature/desk-ia-five-domains` (not yet merged or deployed).

## On this branch

- CEO desk `/desk` rail is grouped **Home · Work · People · Money · More** with
  always-expanded nested anchors to existing section `id`s.
- Main column follows the same map: hybrid Home (metrics + Decisions/Consultant + HQ
  high + Status); Scorecard under Work; People = Organization + Head inbox; Money =
  Budget; More = Intelligence · Diagnostics · Activity · Pairing.
- Pairing and head-inbox anchors are on the rail. No ID renames, domain panes, new APIs
  or Alembic.
- ADR-049; version **0.3.67** (Python package and companion `package.json` kept in
  lockstep). Companion Browse/Manage behavior from 0.3.66 is unchanged.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **496 tests passed**.
- Source contracts in `tests/test_desk_ia_five_domains.py` cover rail groups, section
  order, preserved ids and `__version__ == "0.3.67"`.
- Manual smoke (local or fs-dev after deploy): `GET /desk` — walk each nested rail link;
  confirm Decisions/Consultant above HQ; Scorecard after Status; Pairing last;
  pairing/dispatch/org forms still work.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: **deep visual polish inside companion Browse/Manage**, or fs-dev deploy
of 0.3.67.
