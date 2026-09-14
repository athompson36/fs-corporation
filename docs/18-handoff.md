# Current handoff

Date: 2026-09-14. Version: **0.3.90**. State: **ChatDev-in-worker depth on
`feature/chatdev-worker-depth`.** Tip: **`f85431a`** (venv PYTHONPATH + smoke harden).

## Shipped on feature branch (0.3.90)

- Opt-in `Dockerfile.worker` runs `uv sync` at pinned ChatDev checkout when
  `CHATDEV_ENABLE=1` (fail closed).
- Label `org.fs_corporation.chatdev_deps`; status exposes `worker_image_chatdev.deps_ready`.
- Gateway billed contract test: `SubprocessWorkerRuntime.handle_request(invoke_model)` writes
  `billed_costs` on live invoke.
- Worker entrypoint prepends ChatDev `.venv` site-packages to `PYTHONPATH` when present.
- Optional smoke `scripts/exercise_chatdev_worker_billed.py` fail-closes without image,
  egress, or model key; live invoke requires `FS_CORP_DB` (`--check-only` skips DB).
- ADR-072. No Alembic. Companion lockstep **0.3.90**. Control plane still has no ChatDev
  install.
- Prior on `main`: measurement hardening 0.3.89, provider invoices 0.3.88.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **610 tests, OK** (at tip).
- `cd companion && npm run build`: OK at ship.
- Alembic head **0030** (unchanged).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed follow-ups: merge `feature/chatdev-worker-depth`, fs-dev rebuild with
`FS_CORP_WORKER_CHATDEV=1`, provider CSV/PDF import, optional second worker host, live
documentation fetch, etc.
