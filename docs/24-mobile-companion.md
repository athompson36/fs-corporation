# Mobile CEO companion (M8)

Run FS-Corporation from your phone over **fs-dev LAN HTTPS** or a **private Tailscale network**. The companion is a mobile-first PWA; authority stays on the control-plane API.

## QR-first pairing (v0.3.14)

1. On the CEO desk (`GET /`), open **Phone pairing**.
2. Choose an access level:
   - **Read only** — dashboard, projects, decisions, inbox view only.
   - **User** — read screens plus owner-inbox escalations (department-head pattern).
   - **Admin / CEO mobile** — full companion actions (approve, pause, enroll, dispatch, inbox respond).
3. Tap **Create pairing QR** and scan with the phone (or open the `pair_url` on the device).
4. The companion redeems `#fs-pair={ticket}`, saves API URL + bearer token, and hides actions outside the granted scopes.

The root owner token **never** appears in the QR, URL, or redeem response. Tickets are one-time and expire (default 15 minutes).

### Access levels and scopes

| Level | Scopes | Companion capabilities |
|---|---|---|
| `read_only` | `company.read`, `audit.read`, `consultant.read`, `organization.read` | View-only screens |
| `user` | read_only + `owner.escalate` | View + create escalations |
| `admin` | full `COMPANION_SCOPES` | Approve/reject, pause/resume, enroll, dispatch, inbox respond |

Only the owner may issue pairing tickets (`POST /api/v1/remote-access/pairing`). Redeemed principals are `kind: service` with ids like `companion-{level}-{ticketId[:8]}`.

### Tailscale handoff

- **Same LAN (fs-dev):** set `FS_CORP_PUBLIC_URL=https://192.168.4.100` on the host; QR pair URLs use that origin. No VPN required on Wi‑Fi.
- **Off-LAN:** configure `FS_CORP_TAILSCALE_AUTHKEY` on the host. The auth key is returned **only** on redeem, never in the QR. The PWA cannot join kernel VPN — install the Tailscale app manually, then reopen the companion on the tailnet. A future native shell may consume the auth key via the Tailscale mobile SDK (see [`companion-native/README.md`](../companion-native/README.md)).

## fs-dev production (LAN + Tailscale)

On a host deployed per [25-fs-dev-deployment.md](25-fs-dev-deployment.md):

1. Complete `sudo deploy/fs-dev/install.sh` and configure Caddy on **`https://192.168.4.100`** (phase 1 LAN edge).
2. Set `FS_CORP_PUBLIC_URL=https://192.168.4.100` in `/etc/fs-corporation/env`.
3. Optional: uncomment the Tailscale `https://` block in `deploy/fs-dev/Caddyfile`, set `FS_CORP_TAILSCALE_IP`, and add `FS_CORP_TAILSCALE_AUTHKEY` for off-LAN pairing.
4. On your phone (same LAN or tailnet), scan the desk QR or open the pair URL.

The control API stays on `127.0.0.1:8000`; the phone never talks to port 8000 directly. TLS is terminated by Caddy.

## Dev / Tailscale bind (without Caddy)

1. Install [Tailscale](https://tailscale.com/) on the machine running the control service and on your phone.
2. Start the API bound to your tailnet IP:

```bash
pip install -e .
python3 -m company.service --host 100.x.x.x --port 8000 --allow-remote
```

Replace `100.x.x.x` with `tailscale ip -4` on the host. Do **not** expose port 8000 on the public internet without TLS and a full security review.

3. For companion dev preview against loopback API, set `FS_CORP_ALLOW_CORS=1` on the API host.

## PWA development

```bash
cd companion
npm install
npm run dev
```

Open the dev server on your phone (same Tailscale network) or use `npm run build` and serve `dist/` behind your tailnet.

Pair via CEO desk QR, or paste a ticket manually on the first-run pairing screen (dev fallback).

## Features

| Screen | Actions (scope-gated) |
|---|---|
| Dashboard | Company stats; pause/resume when `company.pause` / `company.resume` |
| Projects | List/detail; enroll and dispatch when `project.enroll` |
| Decisions | Approve/reject when `policy.approve` or `consultant.decide` |
| Inbox | Respond when `company.pause`; escalate when `owner.escalate` |
| Settings | API URL, token, scope summary; clear token to re-pair |

## API endpoints

- `GET /api/v1/dashboard`
- `GET /api/v1/projects`, `GET /api/v1/projects/{id}`
- `POST /api/v1/projects/{id}/dispatch-brief`
- `GET /api/v1/decisions/inbox`
- `GET /api/v1/owner-inbox`, `POST /api/v1/owner-inbox`, `POST /api/v1/owner-inbox/{id}/respond`
- `GET /api/v1/remote-access` — status + `pairing_levels` catalog
- `POST /api/v1/remote-access/pairing` — owner issues QR (`payload.access_level`)
- `POST /api/v1/remote-access/redeem` — companion redeems ticket (no auth)
- `GET /api/v1/events/stream` (SSE; PWA polls every 15s as fallback)
- `POST /api/v1/push/subscriptions`, `POST /api/v1/push/subscriptions/{id}/revoke`, `GET /api/v1/push/status`

## Security

- The phone app is **not** a trust boundary. All mutations go through the same scoped bearer-token API as the CEO desk.
- Pairing tickets are single-use; unknown or expired tickets fail closed.
- Service principals cannot issue new pairing QRs.
- **fs-dev:** use HTTPS via Caddy on LAN or Tailscale; do not expose port 8000 on the LAN.
- **Dev:** Tailscale with `--allow-remote` is acceptable; do not use that bind on the public internet.
- Rotate or revoke compromised device tokens from the CEO desk **Paired devices** list or `POST /api/v1/remote-access/revoke/{principal_id}`.
- Web Push: CEO registers an HTTPS subscription; with VAPID keys configured, `notify_push` delivers live via `pywebpush` and records `applied` or `failed`. The companion PWA auto-registers when the owner token is set (`GET /api/v1/push/status` exposes `application_server_key`). Without keys, deliveries stay `live_unavailable`. PWA polling remains the fallback.

## Native shell (optional)

See [`companion-native/README.md`](../companion-native/README.md) for a thin Expo wrapper around the PWA.
