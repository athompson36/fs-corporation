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

## Verified on fs-dev (2026-09-02)

| Check | Result |
| --- | --- |
| `http://127.0.0.1:8000/api/v1/health` | 200, version 0.3.23 |
| `https://192.168.4.100/` | 200 `text/html` |
| `https://192.168.4.100/api/v1/health` | 200 |
| `sw.js`, `manifest.webmanifest`, SPA deep link | 200 |
| `fs-corporation-api.service` | active (running), enabled |
| `caddy.service` | active, TCP 80 + 443 |
| Bind mount `/media/andrew/Data/fs-corporation` | mounted, in `/etc/fstab` |
| Mac share `/Volumes/fs-dev-data/fs-corporation` | reachable |

The IP site uses Caddy's local CA, so clients see a self-signed warning; the CA
is deliberately not installed into the host trust store.

```bash
./scripts/deploy_to_fs_dev.sh
ssh -t andrew@192.168.4.100 'sudo bash /Data/fs-corporation/run-install.sh'
curl -k -sS -o /dev/null -w "%{http_code}\n" https://192.168.4.100/
```

Passwordless sudo for the deploy commands is installed at
`/etc/sudoers.d/andrew-fs-corporation` (scoped to `run-install.sh`,
`fix_fs_dev_apt.sh`, and the two service restarts).

## Next task

1. Exercise container dispatch and Web Push against fs-dev:
   ```bash
   ssh -t andrew@192.168.4.100 'sudo -u fs-corp /opt/fs-corporation/.venv/bin/python \
     /opt/fs-corporation/scripts/verify_fs_dev_workers.py'
   ```
2. Install the companion PWA from `https://192.168.4.100` on a phone and confirm
   a test push arrives.
3. Furnished HQ room art remains deferred.

See [../deploy/fs-dev/README.md](../deploy/fs-dev/README.md).
