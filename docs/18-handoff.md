# Current handoff

Date: 2026-09-14. Version: **0.3.91**. State: **ChatDev worker native build deps on `main`
and deployed to fs-dev.** Tip: **`da51ffe`** (ship `1c561e9`).

## Merged on main (0.3.91)

- Opt-in `Dockerfile.worker` installs `build-essential` + cairo headers before `uv sync`
  (pycairo); purges toolchain after; keeps `libcairo2`.
- `scripts/deploy_to_fs_dev.sh` sets `FS_CORP_WORKER_CHATDEV=1` and exports it in
  `run-install.sh`.
- ADR-073. No Alembic. Companion lockstep **0.3.91**.
- Prior: ChatDev-in-worker depth 0.3.90.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **611 tests, OK**.
- `cd companion && npm run build`: OK at ship.
- fs-dev health: `{"ok":true,"version":"0.3.91",...}`; worker labels
  `chatdev_enable=1` / `deps=1`; `/opt/chatdev/.venv` present in image.
- Alembic **0030** unchanged.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.

## Next

Owner-directed follow-ups (provider CSV/PDF import, refunds beyond partial_credit,
optional second worker host, live documentation fetch, etc.).
