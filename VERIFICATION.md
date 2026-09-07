# Verification record

Updated 2026-09-07 for **0.3.41** (same-host worker plane). Run on Python 3.14.3 in `.venv`
on macOS. CI additionally runs Python 3.12 and 3.13 (`.github/workflows/ci.yml`).

Earlier records: 0.2.0 ZIP (2026-09-01, Python 3.12.13) and 0.3.13 cosmic-glass desk (2026-09-01).

## Verified in this workspace

- **189 unit tests pass** via `python -m unittest discover -s tests`, run twice: once with a
  clean environment and once with the developer `.env` exported. Both pass.
- `python3 scripts/check_bundle.py` passes: all JSON parses, required context files present,
  and every relative Markdown link resolves.
- `scripts/verify_fs_dev_workers.py` reports worker readiness and `worker_plane` state;
  exit code reflects container dispatch readiness, not plane health.
- Alembic revision chain is linear and single-headed: `0001_initial` through
  `0012_github_webhook_deliveries`.
- Companion TypeScript type-checks (`tsc`) and the main bundle builds in under a second.
  The build as a whole does **not** complete — see "Known drift" below.

## Verified on the fs-dev host (owner-operated, not reproducible from CI)

- Live github.com deliveries returning **200** through Tailscale Funnel at
  `https://fs-dev.tail824ab1.ts.net/api/v1/github/webhooks` for `ping`, `push`, and
  `pull_request` on `athompson36/fs-corp-comp`; host recorded `github.webhook_received`.
- Live feed poll and a live pull request from the production-slice exercise.
- Same-host container dispatch with `FS_CORP_DEFAULT_WORKER_RUNTIME=container`.

These depend on owner credentials and physical hardware. They are evidence of a past run,
not a check any clone can repeat.

## Not tested or not implemented

- Real provider inference at production volume; billed model calls from inside
  `--network none` worker containers (no egress path yet).
- Live ChatDev execution. Slices 1-3 ship the opt-in adapter, worker path, and optional
  image embed; the image carries pinned source, not a full dependency install.
- Production SLO samples; the catalog and manual observations exist, measurement does not.
- Remote GitHub CI against this repository, and any App Store release.
- Live Web Push delivery, which needs owner VAPID keys and a real browser subscription.
- HTTP `429` rate limiting, adapter `cancel`/`fail` mapping tests, consultant
  stale-evidence rejection tests, and role benchmark fixtures. See M10 in
  [docs/14-roadmap.md](docs/14-roadmap.md).
- Actual billed cost and real revenue are not modeled in the schema; only simulated
  credits, estimates, and reservations exist.

## Known drift

- **`cd companion && npm run build` never terminates and emits no service worker.**
  Reproduced twice on 2026-09-07 with `vite` 6.4.3 and `vite-plugin-pwa` 0.21.2. `tsc` passes
  and the main bundle finishes in ~600 ms, then the plugin prints
  `Building src/sw.ts service worker ("es" format)...` and hangs at 0% CPU indefinitely.
  `dist/sw.js` is never written, even though `dist/registerSW.js` is emitted and `index.html`
  references it — so a deployed companion would request a service worker that does not exist.
  `deploy/fs-dev/install.sh` runs this build. Tracked as M10-04 in
  [docs/14-roadmap.md](docs/14-roadmap.md).

- `Company()` applies the schema directly and never runs Alembic. Because
  `CREATE TABLE IF NOT EXISTS` cannot add columns, a database created by the application
  can miss column-only migrations such as `0011_pairing_access_level`. Deployments run
  `alembic upgrade head` explicitly; local databases may not.
- A locally built `fs-corporation-worker:local` image can predate the current
  `Dockerfile.worker`. Rebuild to pick up the entrypoint and `org.fs_corporation.chatdev_*`
  labels; `GET /api/v1/chatdev/status` reports `worker_image_chatdev` from those labels.

Metrics and HQ tiles remain bound to persisted events; no UI surface invents operational
state. Furnished room art is deferred.
