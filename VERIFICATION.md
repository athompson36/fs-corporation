# Verification record

Updated 2026-09-07 for **0.3.47** (companion PWA build fix). Prior: 0.3.46 M10-02;
0.3.45–0.3.42 M10-01; 0.3.41 same-host worker plane. Run on Python 3.14.3 in `.venv` on
macOS / Node 18.20.8. CI additionally runs Python 3.12 and 3.13
(`.github/workflows/ci.yml`).

Earlier records: 0.2.0 ZIP (2026-09-01, Python 3.12.13) and 0.3.13 cosmic-glass desk (2026-09-01).

## Verified in this workspace

- **201 unit tests pass** via `python -m unittest discover -s tests`, including
  `tests.test_service_edges` (bind refusal + SSE frames). Run twice: clean environment and
  with developer `.env` exported.
- `python3 scripts/check_bundle.py` passes: all JSON parses, required context files present,
  and every relative Markdown link resolves.
- `scripts/verify_fs_dev_workers.py` reports worker readiness and `worker_plane` state;
  exit code reflects container dispatch readiness, not plane health.
- Alembic revision chain is linear and single-headed: `0001_initial` through
  `0012_github_webhook_deliveries`.
- **Companion build completes:** `cd companion && npm run build` exits non-interactively
  and emits `dist/sw.js`, `dist/sw-push.js`, `dist/registerSW.js`, and
  `dist/workbox-*.js` (generateSW + `public/sw-push.js`). Companion package **0.3.7**;
  `npm audit` in `companion/` reports 0 vulnerabilities.

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
- Phone offline load / update-on-reload after the generateSW switch (owner smoke check on
  next fs-dev companion rebuild).
- Actual billed cost and real revenue are not modeled in the schema; only simulated
  credits, estimates, and reservations exist.

## Known drift

- Root / `companion-native` Expo tree may still report transitive `npm audit` findings
  (metro, postcss, react-navigation). Those are separate from the Vite companion PWA;
  many need upstream Expo upgrades and are not fixed by `npm audit fix` alone.
- `Company()` now runs Alembic on file-backed databases (0.3.43). Ephemeral `:memory:`
  databases still rely on `apply_schema` alone; that is intentional.
- A locally built `fs-corporation-worker:local` image can predate the current
  `Dockerfile.worker`. Rebuild to pick up the entrypoint and `org.fs_corporation.chatdev_*`
  labels; `GET /api/v1/chatdev/status` reports `worker_image_chatdev` from those labels.

Metrics and HQ tiles remain bound to persisted events; no UI surface invents operational
state. Furnished room art is deferred.
