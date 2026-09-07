# Current handoff

Date: 2026-09-07. Version: 0.3.41. State: **Same-host worker plane on `.101`** + live Funnel webhooks.

## Delivered

- Same-host worker plane: `GET /api/v1/workers/status` → `worker_plane` (`mode=same_host_nic`, `state` healthy/degraded/unset); soft — does not block container dispatch; `scripts/verify_fs_dev_workers.py` warns on stderr; `--require-plane` exits 3.
- ChatDev adapter slice 3: optional ChatDev in worker Docker image (`CHATDEV_ENABLE=1`); entrypoint sets `CHATDEV_HOME` when sdk present; no `CHATDEV_ALLOW_CONTROL_PLANE` leak into containers; `GET /api/v1/chatdev/status` adds `worker_image_chatdev` via fail-closed `docker image inspect` on `FS_CORP_WORKER_IMAGE`.
- ChatDev adapter slice 2: worker subprocess live path when `chatdev: true` + pin-verified `CHATDEV_HOME`; control-plane deny unless `CHATDEV_ALLOW_CONTROL_PLANE=1`; status adds `control_plane_allowed`, `worker_live_ready`.
- ChatDev adapter slice 1: opt-in `ChatDevAdapter` + `company/chatdev_runtime.py`, fixture digest tests, `GET /api/v1/chatdev/status`.
- Funnel: `https://fs-dev.tail824ab1.ts.net/api/v1/github/webhooks`
- Live deliveries **200**: ping, **push**, **pull_request opened** (#4 probe, closed).
- Host `github.webhook_received` for push + PR on repo `1355366113`.
- `verify_fs_dev_pilot.sh` includes Funnel signed-ping exercise.
- Prior: impact-brief API; live feed; merge; production slice.

## Verify

```bash
.venv/bin/python -m unittest tests.test_worker_status tests.test_worker_chatdev tests.test_chatdev_adapter tests.test_worker_dockerfile_chatdev tests.test_m2 tests.test_workers -v
python3 scripts/check_bundle.py
.venv/bin/python scripts/verify_fs_dev_workers.py
```

```bash
FS_CORP_TOKEN_FILE=~/Desktop/fs-corp-owner.token \
  FS_CORP_API_BASE=http://192.168.4.100 \
  python3 scripts/exercise_funnel_webhook.py
```

## Next implementation

- Optional: TailscaleKit; dedicated **second** worker host (separate machine); full ChatDev deps inside worker image for billed model calls; furnished HQ room art deferred.
