# Current handoff

Date: 2026-09-08. Version: **0.3.60**. State: **Track B auto remote placement merged to
`main`, pushed, and deployed to fs-dev** (health `0.3.60`).

## On main / fs-dev

- `FS_CORP_PREFER_REMOTE_WORKERS` (ADR-043): opt-in auto pick first ready host by `(label, id)`
  when `worker_host_id` omitted; none ready → 422; explicit id wins.
- Also on main: remote container-on-agent (0.3.58), `/welcome` + campaign furniture (0.3.59).
- No new Alembic; head `0028_remote_worker_jobs`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **463 passed** before merge.
- Do not commit `local repos/service-department/`.

## Next

Owner picks the next roadmap item (A/B/C follow-ons complete for this sequence).
