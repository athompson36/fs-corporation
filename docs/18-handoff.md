# Current handoff

Date: 2026-09-08. Version: **0.3.58**. State: **Track A remote
container-on-agent is implemented on `feature/remote-container-on-agent`; not merged, pushed,
or deployed by this task.**

## Implemented on this branch

- Remote job claim returns the worker command envelope.
- Claimed jobs expose host-token gateway and lease-renew routes; gateway operations reuse the
  worker allowlist, renew leases, and root stored artifacts on the control plane.
- Completion can record runtime `remote_container`.
- `scripts/remote_worker_agent.py` defaults to mock completion. Explicit
  `FS_CORP_REMOTE_WORKER_RUNTIME=container` runs the configured image with `--network none`,
  relays gateway requests, renews idle leases, detects dead containers, and completes failed
  when Docker, the image, or post-claim setup is unavailable.
- ADR-044 records the boundary. Remote egress, registry control, and automatic placement are
  not included. No Alembic revision was added; head remains `0028_remote_worker_jobs`.
- Release files changed: `company/__init__.py`, `companion/package.json`, `README.md`,
  `VERIFICATION.md`, roadmap/API/decision/handoff docs, and the design/plan records.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **452 passed**.
- `companion/npm run build`: **passed** for companion 0.3.58.
- `scripts/check_bundle.py`: reaches the pre-existing nested local repository and fails on
  `local repos/service-department/README.md` → missing `./LICENSE`.
- Do not commit `local repos/service-department/`.

## Next

1. **Track C — marketing layout.**
2. Track B automatic placement / ADR-043 may still be on a separate branch or stash; do not
   assume it is included in 0.3.58.
