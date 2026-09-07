# FS-Corporation native shell (iOS + Android)

Expo app that pairs via CEO desk QR URL, hands off Tailscale auth (clipboard + open Tailscale app), then loads the companion PWA in a WebView.

## Platform limit

Neither iOS nor Android allows third-party apps to silently inject a Tailscale auth key into the system VPN. After redeem we **copy the key** and open Tailscale; you paste once via **Use an auth key**.

| Platform | Store fallback | In-app paste path |
|---|---|---|
| iOS | App Store Tailscale | profile → Log in → (…) → Use an auth key |
| Android | Play Store `com.tailscale.ipn` | account menu → Log in → Use an auth key |

## Setup

Requires **Node ≥ 20.19.4** (SDK 57). With nvm:

```bash
cd companion-native
nvm use 20
npm install
npx expo start --lan
```

Your phone’s Expo Go must be **SDK 57**. Same Wi‑Fi as the Mac; enter `exp://<mac-lan-ip>:8081` in Expo Go if the project list is empty.

On a physical phone (same LAN as fs-dev for first pair):

1. CEO desk → Create pairing QR.
2. Paste the pair URL into the native app → **Pair & join VPN**.
3. Tailscale opens → **Use an auth key** → Paste (key already on clipboard).
4. Return to the app; it polls the Tailscale companion URL, then opens the WebView.

## Server

`deploy/fs-dev/tailscale-join.sh` joins fs-dev and enables Caddy on the tailnet IP. Auth key lives in `/etc/fs-corporation/secrets.env` only (never in the QR). Redeem returns `vpn.ios_handoff` and `vpn.android_handoff` as `clipboard_open_app` when the key is configured.
