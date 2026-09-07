# Current handoff

Date: 2026-09-07. Version: **0.3.47**. State: **M10-04 companion PWA build fixed**.

## Delivered in 0.3.47

- Companion build no longer hangs: switched from `injectManifest`/`src/sw.ts` to
  `generateSW` with push handlers in `public/sw-push.js` (`importScripts`).
- `vite-plugin-pwa` ^1.2.0; Workbox `mode: "development"` plus a Node 18
  `crypto` polyfill so SW generation exits on fs-dev's Node.
- Verified: `cd companion && npm run build` exits and emits `dist/sw.js` +
  `dist/sw-push.js` (companion **0.3.7**).

## Prior

- 0.3.46 M10-02 test gaps; 0.3.42–0.3.45 M10-01 correctness.

## Verify

```bash
cd companion && npm run build && test -f dist/sw.js && test -f dist/sw-push.js
.venv/bin/python -m unittest discover -s tests
python3 scripts/check_bundle.py
```

## Next implementation

**M10-03** financial model (billed cost / revenue tables), or remaining **M10-04** UI
items (status surface, version display, desk keyboard access, `window.prompt`
replacement).
