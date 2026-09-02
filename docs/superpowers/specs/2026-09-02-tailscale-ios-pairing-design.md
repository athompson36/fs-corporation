# Design: Tailscale QR pairing + iOS native handoff

Date: 2026-09-02. Status: approved (approach A, iOS first).

## Goals

1. Install and join Tailscale on fs-dev using the owner auth key (server-side, automated).
2. Serve companion + API over Tailscale HTTPS (Caddy) in addition to LAN `.100`.
3. Keep auth key **out of the QR**; release only on redeem.
4. iOS native shell: scan/open pair URL → redeem → hand off VPN join → load companion on Tailscale URL.

## Platform constraint (honest)

Tailscale does **not** allow third-party iOS apps to drive VPN login via deep link (security). Best achievable auto-config:

1. Redeem returns `tailscale_auth_key` + `companion_url`.
2. Native app copies the key to the clipboard and opens the Tailscale app (or App Store).
3. One owner action in Tailscale: **Use an auth key** → paste (key already on clipboard).
4. App polls `companion_url` until reachable, then opens the WebView.

Userspace `libtailscale` / TailscaleKit is a future option (app becomes a node without system VPN); out of scope for this slice.

## Server

- Script `deploy/fs-dev/tailscale-join.sh`: install Tailscale apt repo if needed, `tailscale up --auth-key=… --hostname=fs-dev`, write `FS_CORP_TAILSCALE_IP` into `/etc/fs-corporation/env`.
- Deploy stages `FS_CORP_TAILSCALE_AUTHKEY` into `secrets.env` (same path as other secrets).
- Caddy: enable `https://$FS_CORP_TAILSCALE_IP` site (same `lan_site` import). Restart Caddy (not reload).
- Pairing QR `FS_CORP_PUBLIC_URL` stays LAN (`https://192.168.4.100`) so first redeem works on home Wi‑Fi.
- Redeem `base_url` / `companion_url` prefer Tailscale HTTPS when `tailnet_ipv4` or `FS_CORP_TAILSCALE_IP` is known.

## Redeem payload additions

```json
{
  "token": "...",
  "base_url": "https://100.x.x.x",
  "companion_url": "https://100.x.x.x",
  "tailscale_auth_key": "tskey-auth-…",
  "vpn": {
    "provider": "tailscale",
    "status": "configured",
    "ios_handoff": "clipboard_open_app"
  }
}
```

## Native iOS (`companion-native`)

- Scan QR or paste pair URL / ticket.
- POST redeem (against LAN origin from QR).
- If auth key: Clipboard.setString + Linking.openURL(Tailscale / App Store).
- Poll GET `/api/v1/health` on `companion_url` (insecure TLS ok for `tls internal`).
- Persist token + base URL; show WebView.

## Credential hardening (this slice)

- Auth key only in `secrets.env` (640 root:fs-corp), never logs/QR/desk HTML.
- `check_owner_config` already treats it optional; status shows `auth_key_configured` boolean only.
- Document rotation: replace key in `.env`, redeploy, revoke old key in Tailscale admin.

## Non-goals

- Android native handoff
- Dedicated second worker host
- Embedding TailscaleKit userspace VPN
- Changing WireGuard `wg0`

## Acceptance

1. `tailscale status` on fs-dev shows online; `FS_CORP_TAILSCALE_IP` set.
2. `curl -k https://$TAILSCALE_IP/api/v1/health` → 200 from a tailnet client (or from host via tailscale0).
3. Redeem with key configured returns key + `companion_url`; issue QR does not contain key.
4. Native app copies key and opens Tailscale; after paste+connect, WebView loads companion.
5. Unit tests cover redeem fields; no secrets in fixtures beyond `tskey-auth-test-only`.
