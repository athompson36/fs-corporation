# Current handoff

Date: 2026-09-02. Version: 0.3.27. State: **Tailscale join + iOS native VPN handoff.**

## Delivered

- `deploy/fs-dev/tailscale-join.sh` installs/joins Tailscale; Caddy serves tailnet IP.
- Auth key staged via `secrets.env` (never in QR). Redeem returns `companion_url` + `ios_handoff`.
- `companion-native`: paste pair URL → redeem → clipboard auth key → open Tailscale → poll → WebView.

## Owner steps (iOS)

1. Deploy/install (auth key already in local `.env`).
2. On home Wi‑Fi: desk QR → paste URL into native app → **Pair & join VPN**.
3. In Tailscale: **Use an auth key** → Paste (key already copied).
4. Return to app; companion loads on Tailscale HTTPS.

## Next

- Android handoff, or TailscaleKit userspace (true in-app VPN) if one-paste is not enough.
- Dedicated worker host (deferred).
- Furnished HQ room art remains deferred.

```bash
./scripts/deploy_to_fs_dev.sh
ssh andrew@192.168.4.100 'sudo bash ~/fs-corporation-deploy/run-install.sh'
# expect: tailscale ip -4 prints 100.x; remote-access shows auth_key_configured
cd companion-native && npm install && npx expo start --ios
```

See [superpowers/specs/2026-09-02-tailscale-ios-pairing-design.md](superpowers/specs/2026-09-02-tailscale-ios-pairing-design.md).
