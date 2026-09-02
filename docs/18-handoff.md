# Current handoff

Date: 2026-09-02. Version: 0.3.23. State: **fs-dev serving**; phone companion polls healthy after SQLite lock + push auth fixes.

## Delivered

- fs-dev install, Caddy, container workers, owner auth/bootstrap, token rotation.
- Deploy tree on ext4 (`~/fs-corporation-deploy`); CEO desk at `https://192.168.4.100/desk`.
- Serialized SQLite access (concurrent companion polls were returning intermittent 500s).
- Paired companions can register/list their own Web Push subscriptions.
- Companion push UX: iOS Add-to-Home-Screen guidance + **Enable push** button.

## Verified

- Phone (`192.168.4.169`) dashboard/projects/inbox/decisions → 200 after fix.
- Push subscription table still empty until the phone completes iOS A2HS + permission.

## Next task

1. On the phone: Safari → Share → **Add to Home Screen** → open the **icon** (not the Safari tab) → Settings → **Enable push** → allow notifications → **Send test push**.
2. Set a real `VAPID_CONTACT_EMAIL` in `.env` (still `mailto:owner@example.com`) and redeploy secrets if a push provider rejects the placeholder.
3. Owner token copy lives at `~/Desktop/fs-corp-owner.token` on the Mac — keep private.
4. Furnished HQ room art remains deferred.

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
```

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
