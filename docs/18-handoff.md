# Current handoff

Date: 2026-09-07. Version: 0.3.39. State: **Live github.com → Funnel → host (ping, push, pull_request).**

## Delivered

- ChatDev adapter slice 2: worker subprocess live path when `chatdev: true` + pin-verified `CHATDEV_HOME`; control-plane deny unless `CHATDEV_ALLOW_CONTROL_PLANE=1`; status adds `control_plane_allowed`, `worker_live_ready`.
- ChatDev adapter slice 1: opt-in `ChatDevAdapter` + `company/chatdev_runtime.py`, fixture digest tests, `GET /api/v1/chatdev/status`.
- Funnel: `https://fs-dev.tail824ab1.ts.net/api/v1/github/webhooks`
- Live deliveries **200**: ping, **push**, **pull_request opened** (#4 probe, closed).
- Host `github.webhook_received` for push + PR on repo `1355366113`.
- `verify_fs_dev_pilot.sh` includes Funnel signed-ping exercise.
- Prior: impact-brief API; live feed; merge; production slice.

## Verify

```bash
.venv/bin/python -m unittest tests.test_worker_chatdev tests.test_chatdev_adapter tests.test_m2 tests.test_workers -v
python3 scripts/check_bundle.py
```

```bash
FS_CORP_TOKEN_FILE=~/Desktop/fs-corp-owner.token \
  FS_CORP_API_BASE=http://192.168.4.100 \
  python3 scripts/exercise_funnel_webhook.py
```

## Next implementation

- Optional: TailscaleKit; dedicated worker host; ChatDev inside Docker worker image; furnished HQ room art deferred.
