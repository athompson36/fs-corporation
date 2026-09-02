# Current handoff

Date: 2026-09-02. Version: 0.3.23. State: **fs-dev install complete and serving** from the relocated ext4 deploy tree.

## Delivered

- Companion + API + Caddy + container workers on `https://192.168.4.100`.
- Deploy tree at `~/fs-corporation-deploy` (ext4, mode 700); only `/Data/fs-corporation/data` stays on the SMB-exported NTFS volume.
- Stale `/Data/fs-corporation/{repo,run-install.sh,secrets-staging,…}` deploy artifacts removed.
- Owner bootstrap registers a pre-created token file; Alembic uses an absolute `script_location` under `/opt`.
- Secrets installed `0640 root:fs-corp`; staging shredded after install.
- **Owner token rotation:** `Company.rotate_owner_token` + `scripts/rotate_owner_token.py` + host wrapper `~/fs-corporation-deploy/rotate-owner-token.sh`.

## Verified on fs-dev (2026-09-02)

| Check | Result |
| --- | --- |
| Loopback + HTTPS health / SPA / push / workers | 200 / ready |
| Container dispatch of a draft task | `produced` |
| Passwordless sudo for `~/fs-corporation-deploy/run-install.sh` | OK |
| Unit tests / bundle | 136 passed / passed |

## Operator commands

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'

# After sudoers includes rotate-owner-token.sh (re-run setup_fs_dev_passwordless.sh):
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/rotate-owner-token.sh'
# Then read and shred: ~/fs-corporation-deploy/owner.token.rotated
```

## Next task

1. Re-run `./scripts/setup_fs_dev_passwordless.sh` once so sudoers also grants
   `rotate-owner-token.sh`, then rotate the exposed owner token.
2. Set a real `VAPID_CONTACT_EMAIL` in `.env` (still `mailto:owner@example.com`).
3. Install the companion PWA from `https://192.168.4.100` and confirm a test push.
4. Furnished HQ room art remains deferred.

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
