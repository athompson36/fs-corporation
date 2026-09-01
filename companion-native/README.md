# FS-Corporation native shell (optional)

Thin Expo wrapper for installing the CEO companion PWA on iOS/Android home screens.

## Status

Scaffold only. The PWA in [`companion/`](../companion/) is the primary mobile client for v0.3.5.

## Quick start

```bash
cd companion-native
npm install
npx expo start
```

Set `EXPO_PUBLIC_API_URL` in `.env` to your Tailscale control host (e.g. `http://100.x.x.x:8000`).

The app loads the built PWA from that URL in a WebView, or open the PWA directly in Safari/Chrome and use **Add to Home Screen**.

## Future

- Shared TypeScript API client extracted from `companion/src/api/client.ts`
- Push notifications when an owner-request gateway exists
