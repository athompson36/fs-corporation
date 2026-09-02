# FS-Corporation native shell (iOS)

Expo app that pairs via CEO desk QR URL, hands off Tailscale auth (clipboard + open Tailscale app), then loads the companion PWA in a WebView.

## Platform limit

iOS does not allow third-party apps to silently inject a Tailscale auth key. After redeem we **copy the key** and open Tailscale; you paste once via **Use an auth key**.

## Setup

```bash
cd companion-native
npm install
npx expo start --ios
```

On a physical iPhone (same LAN as fs-dev for first pair):

1. CEO desk → Create pairing QR.
2. Paste the pair URL into the native app → **Pair & join VPN**.
3. Tailscale opens → profile → (…) → **Use an auth key** → Paste.
4. Return to the app; it polls the Tailscale companion URL, then opens the WebView.

## Server

`deploy/fs-dev/tailscale-join.sh` joins fs-dev and enables Caddy on the tailnet IP. Auth key lives in `/etc/fs-corporation/secrets.env` only (never in the QR).
