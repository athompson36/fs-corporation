# Current handoff

Date: 2026-09-08. Version: **0.3.63**. State: **Companion Workers tab on
`feature/workers-tab-runbook`** (HEAD 137d81a).

## On branch / pending merge

- Companion primary **Workers** tab: list remote worker hosts with API `state`; create host
  (one-time token shown once); enable/disable/delete when `company.pause` + CEO.
- Client methods on `ApiClient`: `workerHosts`, `createWorkerHost`, `enableWorkerHost`,
  `disableWorkerHost`, `deleteWorkerHost`.
- Nav test expects **5** primary tabs (Home, Projects, Org, Corporate, Workers) plus More.
- Remote-agent runbook in [25-fs-dev-deployment.md](25-fs-dev-deployment.md); companion
  screen table in [24-mobile-companion.md](24-mobile-companion.md).
- Uses existing `/api/v1/worker-hosts*` only; TailscaleKit unchanged; no Alembic.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **475 tests passed**.
- `cd companion && npm run build`: **OK**.
- Do not commit `local repos/service-department/`.

## Next

**Deeper marketing redesign**.
