# Current handoff

Date: 2026-09-14. Version: **0.3.91**. State: **ChatDev worker native build deps shipping
(pushing/deploying).** Tip: **`1c561e9`**.

## Shipping (0.3.91)

- Opt-in `Dockerfile.worker` installs `build-essential` + cairo headers before `uv sync`
  (pycairo); purges toolchain after; keeps `libcairo2`.
- `scripts/deploy_to_fs_dev.sh` sets `FS_CORP_WORKER_CHATDEV=1` and exports it in
  `run-install.sh`.
- ADR-073. No Alembic. Companion lockstep **0.3.91**.
- Prior: ChatDev-in-worker depth 0.3.90.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **611 tests, OK**.
- `cd companion && npm run build`: at ship.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Deploy to fs-dev and confirm worker labels `chatdev_enable=1` / `deps=1`. Owner-directed
follow-ups (provider CSV/PDF import, etc.).
