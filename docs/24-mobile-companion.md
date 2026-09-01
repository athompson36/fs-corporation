# Mobile CEO companion (M8)

Run FS-Corporation from your phone over **fs-dev LAN HTTPS** or a **private Tailscale network**. The companion is a mobile-first PWA; authority stays on the control-plane API.

## fs-dev production (LAN + Tailscale)

On a host deployed per [25-fs-dev-deployment.md](25-fs-dev-deployment.md):

1. Complete `sudo deploy/fs-dev/install.sh` and configure Caddy on **`https://192.168.4.100`** (phase 1 LAN edge).
2. Optional: uncomment the Tailscale `https://` block in `deploy/fs-dev/Caddyfile` and reload Caddy.
3. On your phone (same LAN or tailnet), open **`https://192.168.4.100`** or **`https://100.x.x.x`**.
4. In **Settings**:
   - **API base URL** — leave **empty** for same-origin requests (production build uses empty `VITE_API_BASE` so `/api/*` goes through Caddy). Alternatively set `https://192.168.4.100` explicitly.
   - **Bearer token** — owner token from `/etc/fs-corporation/owner.token` on the host.

The control API stays on `127.0.0.1:8000`; the phone never talks to port 8000 directly. TLS is terminated by Caddy.

## Dev / Tailscale bind (without Caddy)

1. Install [Tailscale](https://tailscale.com/) on the machine running the control service and on your phone.
2. Start the API bound to your tailnet IP:

```bash
pip install -e .
python3 -m company.service --host 100.x.x.x --port 8000 --allow-remote
```

Replace `100.x.x.x` with `tailscale ip -4` on the host. Do **not** expose port 8000 on the public internet without TLS and a full security review.

3. Copy the owner bearer token from `.local/owner.token` (never commit it).

## PWA development

```bash
cd companion
npm install
npm run dev
```

Open the dev server on your phone (same Tailscale network) or use `npm run build` and serve `dist/` behind your tailnet.

In **Settings**, set:

- **API base URL** — `http://100.x.x.x:8000` (your control host tailnet address)
- **Bearer token** — owner token from step 3

## Features (v0.3.5)

| Screen | Actions |
|---|---|
| Dashboard | Company stats, pause/resume, department queue counts |
| Projects | List/detail, enroll, dispatch brief to department heads |
| Decisions | Approve/reject policy and consultant proposals |
| Inbox | Respond to team escalations and feedback |
| Settings | API URL and token |

## API endpoints

- `GET /api/v1/dashboard`
- `GET /api/v1/projects`, `GET /api/v1/projects/{id}`
- `POST /api/v1/projects/{id}/dispatch-brief`
- `GET /api/v1/decisions/inbox`
- `GET /api/v1/owner-inbox`, `POST /api/v1/owner-inbox`, `POST /api/v1/owner-inbox/{id}/respond`
- `GET /api/v1/events/stream` (SSE; PWA polls every 15s as fallback)

## Security

- The phone app is **not** a trust boundary. All mutations go through the same scoped bearer-token API as the CEO desk.
- **fs-dev:** use HTTPS via Caddy on LAN or Tailscale; do not expose port 8000 on the LAN.
- **Dev:** Tailscale with `--allow-remote` is acceptable; do not use that bind on the public internet.
- Rotate tokens via `register_identity` if a device is lost.

## Native shell (optional)

See [`companion-native/README.md`](../companion-native/README.md) for a thin Expo wrapper around the PWA.
