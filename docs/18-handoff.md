# Current handoff

Date: 2026-09-08. Version: **0.3.54**. State: **P4 merged to `main`, pushed, and
deployed to fs-dev.**

## On main / fs-dev

- Alembic `0027_worker_hosts`; CEO registry + heartbeat; `remote_hosts` on `/workers/status`.
- Dispatch still same-host only (ADR-040).
- TailscaleKit stub; SVG furniture from `room_type`; org m5 docs honesty.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **416 passed** (pre-merge).
- fs-dev health: `version` **0.3.54**, HTTP **200**.
- Do not commit `local repos/service-department/`.

## Next

1. **P5** UI pass (deferred chrome), or remote worker agent follow-on.
