# Current handoff

Date: 2026-09-02. Version: 0.3.23. State: fs-dev online at `.100`/`.101`; Mac deploy staged to `/Data/fs-corporation`.

## Delivered

- Local Docker HTTPS + Web Push test path (v0.3.22–0.3.23).
- **fs-dev deploy helper:** `scripts/deploy_to_fs_dev.sh` rsyncs to `/Data/fs-corporation`, stages secrets; host `run-install.sh` needs owner sudo.

## Verification (after sudo install)

```bash
./scripts/deploy_to_fs_dev.sh
ssh -t andrew@192.168.4.100 'sudo bash /Data/fs-corporation/run-install.sh'
curl -k -sS -o /dev/null -w "%{http_code}\n" https://192.168.4.100/
# Mac share: /Volumes/fs-dev-data/fs-corporation
```

## Next task

1. **Owner (now):** run the sudo install command above (password required).
2. Confirm companion at `https://192.168.4.100` + container dispatch; Mac can browse `/Volumes/fs-dev-data/fs-corporation`.
3. Furnished HQ room art remains deferred.

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
