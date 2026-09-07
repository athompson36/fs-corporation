# Current handoff

Date: 2026-09-07. Version: 0.3.41 (unchanged — the audit changed no behavior).
State: **Full-project audit complete.** Integrity fixes applied, documentation trued up to
0.3.41, and genuine gaps opened as M10.

## Audit outcome (2026-09-07)

Covered documentation, all HTTP routes, the schema and its 12 migrations, three UI surfaces,
and the Docker/deploy scripts. Three integrity problems and one stale artifact were fixed:

- `scripts/export_fs_dev_secrets.sh` printed real key values while its header claimed it did
  not. It now emits `PASTE_FROM_LOCAL_ENV` placeholders and reports set/unset on stderr.
- The suite was not hermetic. `tests/test_model_feed_live.py` patched
  `model_provider.model_configured`, which `invoke_model` never calls, so the fail-closed test
  asserted nothing; and `tests/test_owner_config_check.py` was defeated by an `os.environ`
  fallback. Both now go through `tests/env_guard.AmbientEnvIsolatedTestCase`, which also
  replaces the per-test `FS_CORP_WORKER_SCRATCH_HOST` patch in `tests/test_workers.py`.
- Four roadmap items were marked `[x]` with nothing behind them: HTTP `429`, adapter
  `cancel`/`fail` tests, the consultant stale-evidence test, and role benchmark fixtures. All
  unchecked with a note, and carried into M10.
- `fs-corporation-worker:local` predated `Dockerfile.worker` (old entrypoint, no ChatDev
  labels). Rebuilt; `chatdev_status` now reports the pin from image labels.

One new defect surfaced while verifying: **`cd companion && npm run build` never terminates.**
`tsc` passes and the main bundle finishes in ~600 ms, then `vite-plugin-pwa` 0.21.2 prints
`Building src/sw.ts service worker` and hangs at 0% CPU. `dist/sw.js` is never emitted even
though `dist/registerSW.js` is, so a deployed companion requests a service worker that does not
exist, and `install.sh` can appear to stall. Reproduced twice. Opened as the first item of
M10-04; not fixed here, since it is outside the audit's remediation scope and needs a
dependency decision.

Documentation was a v0.3.13 snapshot in places. `VERIFICATION.md` was rewritten against real
evidence, stale "raises NotImplementedError" claims were corrected in `decisions.md` (ADR-014),
`02-architecture.md`, `00-project-context.md`, `23-isolated-workers.md`, and both fs-dev
runbooks. Specs and plans that still read as open work now carry accurate status lines.

New reference material: the full `FS_CORP_*` environment variable table in
[25-fs-dev-deployment.md](25-fs-dev-deployment.md) (including the note that
`FS_CORP_API_HOST`/`FS_CORP_API_PORT` are inert), and in
[16-api-contract.md](16-api-contract.md) the unauthenticated routes, the CEO/HR checks that
apply beyond the route scope, and the real status response shapes.

ADR-021 through ADR-024 record four decisions that shipped with a spec but no ADR: GitHub
webhook ingress, path-scoped Tailscale Funnel, the same-host worker plane, and the ChatDev
adapter slices.

## Verify

Both runs must pass — the second is the one that used to fail:

```bash
env -i PATH="$PATH" HOME="$HOME" .venv/bin/python -m unittest discover -s tests   # clean
set -a && . ./.env && set +a && .venv/bin/python -m unittest discover -s tests    # dirty
python3 scripts/check_bundle.py
.venv/bin/python scripts/verify_fs_dev_workers.py
bash scripts/export_fs_dev_secrets.sh 2>/dev/null   # must contain no real values
```

189 tests pass in both environments; `check_bundle.py` passes.

## Next implementation

**M10-01 in [14-roadmap.md](14-roadmap.md)**, in order:

1. HTTP `429` and request throttling — the contract implies it and nothing implements it.
2. Alembic on startup, or explicit drift detection. `Company()` calls `apply_schema`, and
   `CREATE TABLE IF NOT EXISTS` cannot add columns, so an app-created database can miss
   column-only migrations such as `0011_pairing_access_level`.
3. Atomic idempotency — `remember_command` commits separately from the handler it protects.

Then M10-02 (the three test gaps behind the unchecked claims), M10-03 (billed cost and revenue,
which the currency rule requires and the schema does not model), M10-04 (operator status UI,
version display, desk keyboard access, replacing `window.prompt`).

Still optional and not blocking: TailscaleKit; a dedicated second worker host on a separate
machine; full ChatDev dependencies plus controlled egress for billed model calls from workers;
furnished HQ room art.
