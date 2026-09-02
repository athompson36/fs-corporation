# Current handoff

Date: 2026-09-01. Version: 0.3.11. State: loopback control service, isometric HQ projection of persisted rooms, sourced SLO catalog, fail-closed Web Push, GitHub/feed/container lifecycles, mobile companion, fs-dev runbook. Live adapters remain disabled.

## Delivered

- Origin: `https://github.com/athompson36/fs-corporation.git`.
- Alembic through `0009_slo_observations`.
- CEO desk `#iso` isometric SVG drawn only from `GET /api/v1/headquarters` rooms; `iso-rise` disabled under `prefers-reduced-motion`; list + 2D plan remain.
- Prior: SLO catalog, Web Push, GitHub apply, feed poll, container file gateway, companion PWA, fs-dev.

## Verification

**87 unit tests** pass in `.venv` after `pip install -e .`, including `tests/test_api.py` desk isometric/reduced-motion checks. `python3 scripts/check_bundle.py` passes.

## Limitations

Custom room art and logo/palette remain undecided. SLOs have no production samples. Live GitHub/model/feed/VAPID and container dispatch on `192.168.4.101` still need owner credentials.

## Next task

Owner-supplied live configuration on fs-dev: GitHub App + repo IDs, model credential, approved feed, optional VAPID. Build and exercise `fs-corporation-worker:local` on `192.168.4.101`.

## Commands

```bash
python3 -m company.service --host 127.0.0.1 --port 8000
python3 -m unittest discover -s tests -v
```
