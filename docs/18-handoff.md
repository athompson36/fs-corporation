# Current handoff

Date: 2026-09-14. Version: **0.3.90**. State: **ChatDev-in-worker depth merged to `main`
(pushing/deploying).** Tip: **`475fc8d`** (merge of 0.3.90 ship `2907ca6`; post-review
fix `f85431a`).

## Merged on main (0.3.90)

- Opt-in `Dockerfile.worker` runs `uv sync` at pinned ChatDev when `CHATDEV_ENABLE=1`
  (fail closed); label `org.fs_corporation.chatdev_deps`.
- Status: `worker_image_chatdev.deps_ready`; entrypoint prepends ChatDev `.venv`
  site-packages to `PYTHONPATH` when present.
- Gateway billed contract test + optional smoke
  (`scripts/exercise_chatdev_worker_billed.py`).
- ADR-072. No Alembic. Companion lockstep **0.3.90**. Control plane still has no
  ChatDev install.
- Prior: measurement hardening 0.3.89, provider invoices 0.3.88.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **610 tests, OK**.
- `cd companion && npm run build`: OK at ship.
- Alembic head **0030** (unchanged).
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Deploy to fs-dev. Optional rebuild with `FS_CORP_WORKER_CHATDEV=1`. Owner-directed
follow-ups (provider CSV/PDF import, etc.).
