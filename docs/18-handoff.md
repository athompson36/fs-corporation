# Current handoff

Date: 2026-09-08. Version: **0.3.54**. State: **P4 Scale and presence on
`feature/p4-scale-presence` (ready to merge when owner asks).**

## On this branch

- Alembic `0027_worker_hosts`; CEO registry + heartbeat; `remote_hosts` on `/workers/status`.
- Dispatch still same-host only (ADR-040).
- TailscaleKit stub in `companion-native`; SVG furniture from `room_type` on desk iso.
- Org m5 docs: cross-dept implemented.

## Verification

- Run: `.venv/bin/python -m unittest discover -s tests`
- Do not commit `local repos/service-department/`.

## Next

1. Merge / push / deploy when owner requests (Alembic `0027` on fs-dev).
2. **P5** UI pass (deferred chrome) or remote worker agent follow-on.
