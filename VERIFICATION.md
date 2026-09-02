# Verification record

Created 2026-09-01 on Python 3.12.13 for the 0.2.0 ZIP. Updated 2026-09-01 for 0.3.9 fail-closed Web Push (this workspace ran the unittest suite on Python 3.14.3 in `.venv`).

- 86 unit tests passed, including push subscription/notify lifecycle, feed poll, container file gateway, GitHub apply, companion APIs, QC, HR, and isolated workers.
- Companion PWA builds with `cd companion && npm run build`.
- JSON configurations parsed and required documentation/local Markdown links checked.

Not tested or implemented: real provider inference, live ChatDev, GitHub writes, live feed fetch, live Web Push (VAPID), container image on `192.168.4.101`, remote GitHub CI, or App Store release.

Version 0.3.9 adds CEO HTTPS push enrollment and `notify_push` / owner-inbox delivery attempts that persist `live_unavailable`.
