# Current handoff

Date: 2026-09-08. Version: **0.3.61**. State: **Remote ChatDev egress policy merged to
`main`, pushed, and deploying to fs-dev.**

## On main / fs-dev

- ADR-046: remote claim includes `egress: {mode, docker_network}` (no hostnames). Forbidden
  network names coerce to `none` at claim.
- Container agents attach allowlisted Docker networks only when locally ready; otherwise
  `complete` failed (`remote_egress_unready`). Mock / `mode=none` stay `--network none`.
- No new Alembic; head `0028_remote_worker_jobs`.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **471 passed** before merge.
- Do not commit `local repos/service-department/`.

## Next

**P3 finance** (invoice / refunds / budget-period UX), then TailscaleKit/second-host polish,
then deeper marketing redesign.
