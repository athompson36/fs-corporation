# Current handoff

Date: 2026-09-09. Version: **0.3.63**. State: **Companion Workers tab merged to
`main`, pushed, and deployed to fs-dev** (health `0.3.63`).

## On main / fs-dev

- Companion primary **Workers** tab: list remote worker hosts with API `state`; create host
  (one-time token shown once); enable/disable/delete when `company.pause` + CEO.
- Client methods: `workerHosts`, `createWorkerHost`, `enableWorkerHost`,
  `disableWorkerHost`, `deleteWorkerHost`.
- Remote-agent runbook in [25-fs-dev-deployment.md](25-fs-dev-deployment.md):
  `FS_CORP_CONTROL_URL` must be reachable from the agent; `base_url` is identification only.
- Existing `/api/v1/worker-hosts*` only; TailscaleKit unchanged; no Alembic
  (head `0028_remote_worker_jobs`).

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **476 tests passed**.
- `cd companion && npm run build`: **OK**.
- fs-dev health: **0.3.63**.
- Do not commit `local repos/service-department/`.

## Next

**Deeper marketing redesign**.
