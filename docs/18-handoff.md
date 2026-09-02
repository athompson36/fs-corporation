# Current handoff

Date: 2026-09-02. Version: 0.3.25. State: **fs-dev live; VAPID contact set to owner mailbox.**

## Delivered

- M9 phase 1 + same-host phase 2 (container default, `.101` presence).
- `VAPID_CONTACT_EMAIL=mailto:athompson36@gmail.com` in local `.env` (deployed via secrets.env).

## Next task

1. Follow-on: dedicated worker host / egress policy on `.101` if needed beyond labels+presence.
2. Furnished HQ room art remains deferred.

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
```

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
