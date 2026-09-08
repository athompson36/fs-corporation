# Current handoff

Date: 2026-09-08. Version: **0.3.53**. State: **P3 follow-on (benchmarks + work-order
replay) merged to `main`, pushing, and deploying to fs-dev.**

## On main

- `choose_model` prefers max benchmark **quality** among eligible profiles (ADR-039).
- Alembic `0026_work_order_replays`; authorize / complete-outcome / replay APIs.
- P3 durable finance; P2 live ops; P1 Settings.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **408 passed**
- Do not commit `local repos/service-department/`.

## Next

1. Smoke is optional for this API-first slice.
2. **P4 Scale and presence** design (second worker host · TailscaleKit · furnished HQ art).
