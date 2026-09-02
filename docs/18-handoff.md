# Current handoff

Date: 2026-09-02. Version: 0.3.23. State: **fs-dev serving**; CEO desk now on HTTPS at `/desk` for phone pairing.

## Delivered (this session)

- Deploy tree on ext4 (`~/fs-corporation-deploy`); stale `/Data` deploy artifacts removed.
- Owner token rotated; rotate sudoers grant installed.
- `/desk` exposes the CEO desk through Caddy (companion owns `/`).
- Desk UI accepts a pasted owner token for pairing QR issuance.
- `scripts/issue_pairing_ticket.py` for CLI pairing URLs.

## Operator commands

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'

# Phone push path
# 1. Store then shred: ~/fs-corporation-deploy/owner.token.rotated
# 2. Mac: https://192.168.4.100/desk → paste token → Create pairing QR
# 3. Phone: open pair_url, allow notifications, Add to Home Screen
# 4. Companion → Send test push
```

## Next task

1. **You:** store `~/fs-corporation-deploy/owner.token.rotated`, then
   `ssh andrew@192.168.4.100 'shred -u ~/fs-corporation-deploy/owner.token.rotated'`.
2. Set a real `VAPID_CONTACT_EMAIL` in `.env` (still `mailto:owner@example.com`) and redeploy secrets.
3. Pair a phone and confirm a test push arrives.
4. Furnished HQ room art remains deferred.

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
