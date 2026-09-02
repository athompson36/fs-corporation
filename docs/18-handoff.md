# Current handoff

Date: 2026-09-01. Version: 0.3.12. State: loopback control service, room detail from persisted expansion work, isometric HQ projection, sourced SLO catalog, fail-closed Web Push, GitHub/feed/container lifecycles, mobile companion, fs-dev runbook. Live adapters remain disabled.

## Delivered

- Origin: `https://github.com/athompson36/fs-corporation.git`.
- Alembic through `0009_slo_observations`.
- `GET /api/v1/headquarters/rooms/{id}` and CEO desk room selection show persisted tasks, staff, deliverables, simulated costs and related decisions. Empty staff/deliverable lists stay empty. No occupancy count.
- Prior: isometric HQ SVG, SLO catalog, Web Push, GitHub apply, feed poll, container file gateway, companion PWA, fs-dev.

## Verification

**90 unit tests** pass in `.venv` after `pip install -e .`, including `tests/test_m6.py` room-detail tests and `tests/test_api.py` desk nav checks. `python3 scripts/check_bundle.py` passes.

## Limitations

Custom room art and logo/palette remain undecided. SLOs have no production samples. Live GitHub/model/feed/VAPID and container dispatch on `192.168.4.101` still need owner credentials.

## Next task

Owner-supplied live configuration on fs-dev: GitHub App + repo IDs, model credential, approved feed, optional VAPID. Build and exercise `fs-corporation-worker:local` on `192.168.4.101`.

## Commands

```bash
python3 -m company.service --host 127.0.0.1 --port 8000
python3 -m unittest discover -s tests -v
```
