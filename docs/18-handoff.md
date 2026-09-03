# Current handoff

Date: 2026-09-02. Version: 0.3.27. State: **iOS Tailscale VPN + pairing verified.**

## Delivered

- fs-dev on Tailscale `100.118.234.20`; Caddy HTTP+HTTPS on LAN and tailnet.
- Native iOS: pair URL → redeem → Tailscale auth key → companion WebView.
- Container default, `.101` gateway egress, VAPID contact configured.

## Owner — continue from here

1. In the Expo app, tap **Open companion** (or wait for auto-load). Companion URL: `http://100.118.234.20` (off-LAN over Tailscale).
2. Optional push: Safari → `http://100.118.234.20` → **Add to Home Screen** → **Enable push** in settings (iOS requires home-screen PWA).
3. CEO desk pairing QR (on LAN): `https://192.168.4.100/desk`

## Next implementation (deferred)

- Android native handoff; TailscaleKit one-tap join.
- Dedicated worker host.
- Furnished HQ room art.
