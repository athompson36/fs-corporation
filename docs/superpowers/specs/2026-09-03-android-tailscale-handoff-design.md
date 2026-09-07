# Design: Android Tailscale pairing handoff

Date: 2026-09-03. Status: implemented (extends iOS clipboard handoff).

## Goal

Same off-LAN pairing path on Android as iOS: redeem → clipboard auth key → open Tailscale → one paste → poll companion → WebView.

## Constraint

Android also forbids silent third-party injection of a Tailscale auth key into the system VPN without TailscaleKit / userspace VPN (out of scope). Clipboard + open app is the honest path.

## Changes

1. Redeem `vpn.android_handoff: "clipboard_open_app"` when `FS_CORP_TAILSCALE_AUTHKEY` is set (mirrors `ios_handoff`).
2. `companion-native/tailscale.ts` — Platform store URL (Play vs App Store) + platform-specific paste instructions.
3. `App.tsx` uses that helper; Android hint text on the pair screen.

## Non-goals

- TailscaleKit / userspace node
- Auto-inject auth key via Intent extras (undocumented / unstable)
- Dedicated second worker host

## Acceptance

1. Redeem with auth key returns both `ios_handoff` and `android_handoff`.
2. On Android Expo Go: Pair & join VPN copies key and opens Tailscale or Play Store.
3. After paste+connect, WebView loads `companion_url` on the tailnet.
