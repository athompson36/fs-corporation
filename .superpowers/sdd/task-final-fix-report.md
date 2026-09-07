# Final whole-branch fix report

Date: 2026-09-07

- Changed the catalog/default worker runtime to `subprocess` and added effective-setting
  plus worker-status regression coverage.
- App startup now builds its rate-limit policy from company effective settings, so
  persisted overlays apply after restart while remaining restart-required.
- `FS_CORP_PUBLIC_URL` now accepts empty or an HTTPS URL with a host, without userinfo
  or a fragment.
- Settings listing now degrades an individually invalid env/overlay value to its
  catalog default instead of failing the entire endpoint.
- ChatDev status no longer reports company-overlay control over the isolated-worker
  gate, which workers intentionally bypass inside their isolated boundary.
- Reset-all now removes only editable catalog overlays.
- Repaired the dispatch-recommend model-status reference so its existing live-path
  test patches the dependency actually called.
- Verification: `.venv/bin/python -m unittest discover -s tests` — 382 passed.
- Verification: `cd companion && npm run build` — passed, 33 modules transformed.
- Deferred: existing Starlette deprecation and SQLite `ResourceWarning`; no desk
  Settings expansion, deployment, or service-department changes.
