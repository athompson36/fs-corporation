# Design: Tailscale Funnel for GitHub webhooks

Date: 2026-09-07. Status: opted-in on fs-dev; live serve blocked on Tailscale Funnel consent.

## Goal

Expose **only** `POST /api/v1/github/webhooks` to the public internet via Tailscale Funnel so github.com can deliver signed events to fs-dev without a public LAN IP or full-site exposure.

## Constraints

- Opt-in: `FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS=1` (default off).
- Path-scoped Funnel mount — never Funnel the companion root `/`.
- HMAC (`GITHUB_WEBHOOK_SECRET`) remains the auth; Funnel is transport only.
- Tailscale admin must allow Funnel for the node (ACL `funnel` attribute).
- Does not replace LAN/Caddy Tailscale private sites.

## Design

1. `deploy/fs-dev/tailscale-funnel-webhooks.sh` with `apply` / `remove` / `status`:
   - `apply`: `tailscale funnel --bg --https=443 --set-path=/api/v1/github/webhooks http://127.0.0.1:8000/api/v1/github/webhooks`
   - `remove`: reset funnel config for that path / `tailscale funnel reset` scoped carefully
   - `status`: parse `tailscale funnel status` JSON/text for public URL
2. `install.sh` / `run-install` calls apply when env flag is set (after join).
3. `GET /api/v1/github/status` adds `funnel_webhooks` `{enabled, public_url}` from a probe (no secrets).
4. Owner checklist documents Funnel ACL + App webhook URL = `{public_url}`.

## Non-goals

- TailscaleKit
- Funneling CEO desk / companion
- Dedicated worker host

## Acceptance

1. With flag unset, Funnel not applied; status shows disabled.
2. With flag set on a Funnel-capable node, status returns a `*.ts.net` URL ending in `/api/v1/github/webhooks`.
3. Unit test covers status parsing fail-closed when CLI missing.
