# Current handoff

Date: 2026-09-02. Version: 0.3.18. State: Live GitHub, models, feeds, Docker dev container dispatch, Web Push (VAPID), fs-dev production worker install path.

## Delivered

- **v0.3.17 pushed** (`1413f7b`): Web Push (VAPID) adapter, `GET /api/v1/push/status`, verify/generate scripts.
- **fs-dev workers (v0.3.18):** `install.sh` installs Docker, builds worker image, worker scratch dir, bootstrap grants; `GET /api/v1/workers/status`, `scripts/verify_fs_dev_workers.py`; native `exercise_container_dispatch.py --db` for loopback API.

## Verification

```bash
python3 -m unittest discover -s tests -v
# Docker dev:
python3 scripts/exercise_container_dispatch.py \
  --token-file <(docker compose exec -T api cat /data/owner.token) \
  --task-id container-pilot-$(date +%s)
# fs-dev host (after install.sh):
sudo -u fs-corp /opt/fs-corporation/.venv/bin/python scripts/verify_fs_dev_workers.py
sudo -u fs-corp FS_CORP_DB=/var/lib/fs-corporation/company.db \
  /opt/fs-corporation/.venv/bin/python scripts/exercise_container_dispatch.py \
  --base http://127.0.0.1:8000 \
  --token-file /etc/fs-corporation/owner.token \
  --db /var/lib/fs-corporation/company.db \
  --task-id container-pilot-$(date +%s)
```

## Next task

1. **Owner:** run `install.sh` on fs-dev host; add live secrets to `/etc/fs-corporation/secrets.env`; generate VAPID keys for push.
2. **Engineering:** exercise container dispatch on physical host `192.168.4.100`; optional dedicated worker NIC `.101` when second interface is configured.
3. Furnished HQ room art remains deferred.

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
