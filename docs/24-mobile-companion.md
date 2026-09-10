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
| `admin` | full `COMPANION_SCOPES` | Approve/reject, pause/resume, enroll, dispatch, inbox respond, organization and HQ writes |

Only the owner may issue pairing tickets (`POST /api/v1/remote-access/pairing`). Redeemed principals are `kind: service` with ids like `companion-{level}-{ticketId[:8]}`.

An `admin` principal also satisfies the CEO-actor check in application code (ADR-034), so policy
and consultant decisions, owner-inbox responses, HR actions (staffing scan, promotion proposals,
worker sprite/profile) and division proposals succeed from a paired phone. Root-authority
operations stay owner-only: pairing issue/list/revoke, revenue, budget periods, policy rollback,
model assignment, feed enrollment and SLO observations.

The client never decides its own scopes. `GET /api/v1/session` returns `principal_id`, `kind`,
`access_level` and `scopes` for the presented bearer token (authentication only, no extra scope,
so a read-only device can learn it is read-only). The companion calls it on load and merges the
result into stored settings, which self-heals a native shell or stale `localStorage` that has no
scopes. Where a control is unavailable the companion shows the missing scope instead of hiding
the section silently.

### Tailscale handoff

- **Same LAN (fs-dev):** set `FS_CORP_PUBLIC_URL=https://192.168.4.100` on the host; QR pair URLs use that origin. First redeem must happen on Wi‑Fi.
- **Off-LAN:** `FS_CORP_TAILSCALE_AUTHKEY` in `secrets.env`. Key returns **only** on redeem. `deploy/fs-dev/tailscale-join.sh` joins the server and enables Caddy on the tailnet IP.
- **Native (`companion-native`):** iOS and Android copy the auth key, open Tailscale for one-paste **Use an auth key**, poll `companion_url`, then load the PWA. (Neither OS allows silent third-party VPN injection.)
- **PWA alone** cannot join kernel VPN — use the native shell for off-LAN auto-handoff.

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

Bottom navigation is five domain tabs — **Home · Work · People · Money · More**. **Home** is the
Needs-you queue built from persisted pending decisions and owner-inbox requests, with inline
approve/reject/respond actions when scopes allow; creating an escalation remains under **More →
Inbox**. **Work** groups Projects, Corporate and Workers. **People** opens Organization. **Money**
opens Finance. **More** groups Decisions, Inbox, Diagnostics and Settings behind a segmented
switcher. The Home badge is the pending-decision plus owner-request count. At narrow widths
(including 320px), labels use compact type and may wrap to reduce truncation; exact rendering still
depends on the browser's font metrics. Every write reports its outcome on an inline status line
next to the control, not only at the top of the page.

| Screen | Actions (scope-gated) |
|---|---|
| Home | Needs-you queue; persisted status strip; pause/resume when `company.pause` / `company.resume` |
| Work → Projects | List/detail; local candidates + enroll; assign GitHub by upstream address; dispatch with Recommend / templates / budget chips / Valid values when `project.enroll` |
| Work → Corporate | Scorecard, objectives, industry packs, divisions, promotions, staffing proposals, cross-department requests, activity, default floorplan |
| Work → Workers | List remote worker hosts (API `state`); create host (one-time token shown once); enable/disable/delete when `company.pause` + CEO |
| People | Organization catalog and roster; departments, heads, positions, assignments, reorder, activation and worker card when `organization.write` |
| Money | Finance sub-tabs **Overview · Invoices · Adjustments · Periods**; summary (gross/net/adjustments/revenue); create invoices with expandable line detail; void/partial-credit refunds via billed-cost picker (`GET /finance/billed-costs`); set/close budget periods with confirm + next-period prefill (CEO + `company.pause`). Dollar amounts use display-only `formatUsd`; API payloads stay integer cents. |
| More → Decisions | Approve/reject when `policy.approve` or `consultant.decide` |
| More → Inbox | Respond when `company.pause`; escalate when `owner.escalate` |
| More → Diagnostics | Parallel live probes: health, workers, model, github, push, chatdev, feeds, slos, local-repos |
| More → Settings | Connection (API URL, token, session principal/scopes, clear to re-pair); **Runtime** editable overlays with source badge and restart notice when `restart_required`; **Feeds** approve/pause/revoke/poll (HTTPS only; watchlists template-only); **Models** read-only profiles + pointer to global cents setting; read-only **Host** (LAN IP, worker NIC, gateway egress); **Secrets** configured/missing list (no values). PATCH/reset when `company.pause` + CEO/admin companion |

## API endpoints

- `GET /api/v1/session` — principal, kind, access level and scopes for the bearer token
- `GET /api/v1/dashboard`
- `GET /api/v1/projects`, `GET /api/v1/projects/{id}`
- `POST /api/v1/projects/{id}/dispatch-brief`
- `POST /api/v1/projects/{id}/github-assign` — upstream URL/`owner/repo` → same-owner `{repo}-corp` enrollment
- `GET /api/v1/local-repos` — folders under `local repos/` as enroll candidates
- `GET /api/v1/decisions/inbox`
- `GET /api/v1/owner-inbox`, `POST /api/v1/owner-inbox`, `POST /api/v1/owner-inbox/{id}/respond`
- `GET /api/v1/remote-access` — status + `pairing_levels` catalog
- `POST /api/v1/remote-access/pairing` — owner issues QR (`payload.access_level`)
- `POST /api/v1/remote-access/redeem` — companion redeems ticket (no auth)
- `GET /api/v1/events/stream` (SSE; PWA polls every 15s as fallback)
- `POST /api/v1/push/subscriptions`, `POST /api/v1/push/subscriptions/{id}/revoke`, `GET /api/v1/push/status`
- `GET /api/v1/settings`, `PATCH /api/v1/settings`, `POST /api/v1/settings/reset`, `GET /api/v1/settings/secrets-status`
- `GET /api/v1/feeds`, `POST /api/v1/feeds`, `POST /api/v1/feeds/{id}/pause`, `POST /api/v1/feeds/{id}/revoke`, `POST /api/v1/feeds/{id}/poll`
- `GET /api/v1/model-profiles`
- `GET /api/v1/finance/summary`, `billed-costs`, invoices, adjustments, budget-periods (+ create/close)
- `GET /api/v1/worker-hosts` — list registered remote hosts with computed `state`
- `POST /api/v1/worker-hosts` — create host (`label`, https `base_url`); response includes one-time `token` (CEO + `company.pause`)
- `POST /api/v1/worker-hosts/{id}/enable`, `POST /api/v1/worker-hosts/{id}/disable` — CEO enable/disable
- `DELETE /api/v1/worker-hosts/{id}` — CEO delete host

## Security

- The phone app is **not** a trust boundary. All mutations go through the same scoped bearer-token API as the CEO desk.
- Pairing tickets are single-use; unknown or expired tickets fail closed.
- Service principals cannot issue new pairing QRs.
- **fs-dev:** use HTTPS via Caddy on LAN or Tailscale; do not expose port 8000 on the LAN.
- **Dev:** Tailscale with `--allow-remote` is acceptable; do not use that bind on the public internet.
- Rotate or revoke compromised device tokens from the CEO desk **Paired devices** list or `POST /api/v1/remote-access/revoke/{principal_id}`.
- Web Push: paired **admin** companions and the CEO can register an HTTPS subscription.
  With VAPID keys configured, `notify_push` delivers live via `pywebpush` and records
  `applied` or `failed`. The companion PWA auto-registers when `company.pause` is in
  scope (`GET /api/v1/push/status` exposes `application_server_key`). Without keys,
  deliveries stay `live_unavailable`. PWA polling remains the fallback.
- **iOS:** Web Push only works from a home-screen PWA (Share → Add to Home Screen),
  not from a Safari tab. Accept the local CA warning for `https://192.168.4.100` first.

## Native shell (optional)

See [`companion-native/README.md`](../companion-native/README.md) for a thin Expo wrapper around the PWA.
