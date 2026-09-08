# Current handoff

Date: 2026-09-08. Version: **0.3.53**. State: **P3 follow-on (benchmarks + work-order
replay) on `feature/p3-benchmarks-replay`.**

## This branch

- `choose_model` prefers max benchmark **quality** among eligible profiles (ADR-039).
- Alembic `0026_work_order_replays`; authorize / complete-outcome / replay APIs.
- Consultant `to_work_order` writes the first ledger row.

## Also on main

- P3 durable finance; P2 live ops; P1 Settings.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **408 passed**
- Do not commit `local repos/service-department/`.

## Next

1. Merge/push/deploy when owner requests.
2. **P4 Scale and presence** design (second worker host · TailscaleKit · furnished HQ art).
