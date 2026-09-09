# Current handoff

Date: 2026-09-08. Version: **0.3.63**. State: **Companion Workers tab on
`feature/workers-tab-runbook`**.

## On branch / pending merge

- Companion primary **Workers** tab: list remote worker hosts with API `state`; create host
  (one-time token shown once); enable/disable/delete when `company.pause` + CEO.
- Client methods on `ApiClient`: `workerHosts`, `createWorkerHost`, `enableWorkerHost`,
  `disableWorkerHost`, `deleteWorkerHost`.
- Nav test expects **5** primary tabs (Home, Projects, Org, Corporate, Workers) plus More.
- Remote-agent runbook in [25-fs-dev-deployment.md](25-fs-dev-deployment.md); companion
  screen table in [24-mobile-companion.md](24-mobile-companion.md).
- Runbook clarifies that remote agents dial `FS_CORP_CONTROL_URL`, while worker-host
  `base_url` is identification metadata only.
- Worker-token Copy reports success/failure through inline action status and selects the token
  for manual copy when the Clipboard API is unavailable. Narrow tab labels may wrap at 320px.
- Uses existing `/api/v1/worker-hosts*` only; TailscaleKit unchanged; no Alembic.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **476 tests passed**.
- `cd companion && npm run build`: **OK**.
- Do not commit `local repos/service-department/`.

## Next

**Deeper marketing redesign**.
