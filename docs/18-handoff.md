# Current handoff

Date: 2026-09-11. Version: **0.3.67**. State: **desk five-domain IA merged to
`main`, pushed, and deployed to fs-dev** (health `0.3.67`).

## On main / fs-dev

- CEO desk `/desk` rail is grouped **Home · Work · People · Money · More** with
  always-expanded nested anchors to existing section `id`s.
- Main column follows the same map: hybrid Home (metrics + Decisions/Consultant + HQ
  high + Status); Scorecard under Work; People = Organization + Head inbox; Money =
  Budget; More = Intelligence · Diagnostics · Activity · Pairing.
- Pairing and head-inbox anchors are on the rail. No ID renames, domain panes, new APIs
  or Alembic.
- ADR-049; version **0.3.67** (Python package and companion `package.json` lockstep).
  Companion Browse/Manage behavior from 0.3.66 is unchanged.
- Tip: `b7aabf0` (includes scrollable rail + doc nits after final review).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **496 tests passed**.
- fs-dev health: **0.3.67**; `/desk` **200** with Home · Work · People · Money · More
  rail groups and nested anchors through `#pairing`.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed: **deep visual polish inside companion Browse/Manage**.
