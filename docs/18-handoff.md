# Current handoff

Date: 2026-09-02. Version: 0.3.23. State: **fs-dev install complete and serving.** Companion answers on `https://192.168.4.100`, API healthy on loopback.

## Delivered

- Local Docker HTTPS + Web Push test path (v0.3.22–0.3.23).
- **fs-dev deploy helper:** `scripts/deploy_to_fs_dev.sh` rsyncs to `/Data/fs-corporation`, stages secrets; host `run-install.sh` applies them as root.
- **fs-dev install now converges.** Three install-blocking defects fixed:
  - Companion `node_modules` is rebuilt from scratch each run. An interrupted
    install had left packages half-extracted (missing `.mjs`/`.d.ts`), which
    `npm install` treats as satisfied and Vite then cannot resolve.
  - Caddy no longer serves HTTP/3. `wg0` owns UDP 443 on this host, so the QUIC
    listener could never bind and aborted every config load.
  - Caddy is restarted, never reloaded. `admin off` disables the API that
    `caddy reload` posts to, and a failed reload wedges the unit in `reloading`
    until systemd kills it every 90s — this is what made the install hang.
  - `skip_install_trust` is set because the `caddy` service user cannot sudo to
    install the local root CA, which also aborted config load.

- **Owner authentication now works on fs-dev.** The installer writes
  `owner.token` as root before the service first runs, and `bootstrap_owner`
  treated an existing file as proof of a registered identity. The database had
  zero identities and every authenticated request returned 401. It now
  registers a pre-existing token, and refuses to start if an owner is already
  registered under a different one.
- **Secrets are installed 0640 root:fs-corp**, not 0600. The API runs as
  `fs-corp` and could not read `vapid-private.pem`, so push status returned 500.
- **Staged secrets are shredded after install.** `/Data` is NTFS mounted 0777
  and re-exported over SMB, so `secrets-staging/` exposed the GitHub App key,
  the VAPID private key and the model API keys to every local user and share
  client. `chmod` cannot fix this — the mount forces the mode.
- `scripts/deploy_to_fs_dev.sh` had drifted from the host copy and would have
  reverted `INSTALL_DIR` to NTFS. It now emits what actually works, waits for
  health instead of racing the restart, and no longer echoes the owner token.

## Verified on fs-dev (2026-09-02)

| Check | Result |
| --- | --- |
| `http://127.0.0.1:8000/api/v1/health` | 200, version 0.3.23 |
| `https://192.168.4.100/` | 200 `text/html` |
| `https://192.168.4.100/api/v1/health` | 200 |
| `sw.js`, `manifest.webmanifest`, SPA deep link | 200 |
| Owner bearer token on `/api/v1/company` | 200 |
| `/api/v1/push/status` | `configured: true, live: true` |
| `/api/v1/workers/status` | `container_dispatch_ready: true` |
| Container dispatch of a draft task | `produced`, artifact hash recorded |
| `fs-corporation-api.service` | active (running), enabled |
| `caddy.service` | active, TCP 80 + 443 |
| Bind mount `/media/andrew/Data/fs-corporation` | mounted, in `/etc/fstab` |
| Mac share `/Volumes/fs-dev-data/fs-corporation` | reachable |
| Unit tests / bundle check | 132 passed / passed |

The IP site uses Caddy's local CA, so clients see a self-signed warning; the CA
is deliberately not installed into the host trust store.

```bash
./scripts/deploy_to_fs_dev.sh
ssh -t andrew@192.168.4.100 'sudo bash /Data/fs-corporation/run-install.sh'
curl -k -sS -o /dev/null -w "%{http_code}\n" https://192.168.4.100/
```

## Deploy tree moved off the SMB share

The old layout granted passwordless root to
`/bin/bash /Data/fs-corporation/run-install.sh`. `/Data` is NTFS mounted 0777
and bind-mounted into the Samba export, so that script was writable by every
local user and every client of the `fs-dev-data` share — a local root path, and
`chmod` cannot fix it because the mount forces the mode.

`scripts/deploy_to_fs_dev.sh` now stages to `~/fs-corporation-deploy` on ext4:
deploy root `0700`, `run-install.sh` `0700`, staged keys `0600`. Only
`/Data/fs-corporation/data` (database, companion dist, worker scratch) stays on
the big disk and the share. `scripts/setup_fs_dev_passwordless.sh` refuses to
install the rule if the granted script sits on a mount that cannot enforce
permissions.

Swapping the rule needs one password prompt:

```bash
./scripts/deploy_to_fs_dev.sh
./scripts/setup_fs_dev_passwordless.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
```

Note that `/Data/fs-corporation/data/company.db` is still world-writable through
the share by virtue of the NTFS mode. It holds no plaintext secrets (identity
tokens are hashed), but a share client could tamper with company state.

## Next task

1. After the sudoers swap, delete the stale `/Data/fs-corporation/{repo,
   run-install.sh,secrets-staging,env.prepared,*.sudoers}`.
2. Rotate the owner token. It was echoed to the terminal by earlier installs
   (now fixed). There is no rotation command yet: `bootstrap_owner` fails closed
   when the file stops matching the registered identity, so rotation needs a
   deliberate flow that updates both.
3. Set a real `VAPID_CONTACT_EMAIL` in `.env`; it is still the placeholder
   `mailto:owner@example.com`, which push services may reject.
4. Install the companion PWA from `https://192.168.4.100` on a phone and confirm
   a test push arrives end to end.
5. Furnished HQ room art remains deferred.

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
