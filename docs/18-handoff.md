# Current handoff

Date: 2026-09-08. Version: **0.3.60**. State: **Track B auto remote placement recovered
onto `feature/auto-remote-placement` from stash (rebased onto main after A+C).** Not merged,
pushed, or deployed yet.

## On this branch

- `FS_CORP_PREFER_REMOTE_WORKERS` (ADR-043): when true and `worker_host_id` omitted, pick the
  first ready host by `(label, id)`; none ready → 422. Explicit id still wins.
- Includes main through v0.3.59 (remote container + `/welcome` + campaign furniture).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **463 passed** after recovery.
- Do not commit `local repos/service-department/`.

## Next

1. Merge / push / deploy when owner requests.
2. Drop recovery stashes after merge if still present (`stash@{0..2}` from B WIP).
