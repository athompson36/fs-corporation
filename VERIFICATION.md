# Verification record

Created 2026-09-01 on Python 3.12.13 for the 0.2.0 ZIP. Updated 2026-09-01 for 0.3.12 room detail (this workspace ran the unittest suite on Python 3.14.3 in `.venv`).

- 90 unit tests passed, including room-detail persistence/empty-staff checks, desk nav HTML, isometric/reduced-motion, SLO observations, push, feed, container gateway, GitHub apply, companion APIs, QC, HR, and isolated workers.
- Companion PWA builds with `cd companion && npm run build`.
- JSON configurations parsed and required documentation/local Markdown links checked.

Not tested or implemented: real provider inference, live ChatDev, GitHub writes, live feed fetch, live Web Push (VAPID), production SLO samples, container image on `192.168.4.101`, remote GitHub CI, or App Store release.

Version 0.3.12 adds `GET /api/v1/headquarters/rooms/{id}` so a selected room opens persisted tasks, staff, deliverables and decisions. Unknown rooms fail closed. No invented occupancy.
