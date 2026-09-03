# Current handoff

Date: 2026-09-02. Version: 0.3.27. State: **iOS Tailscale + live pilot on fs-dev.**

## Delivered

- iOS: pair → Tailscale → companion on `http://100.118.234.20`.
- Live pilot on fs-dev: GitHub App + OpenAI/Anthropic + container dispatch `produced`.
- `scripts/verify_fs_dev_pilot.sh` — repeatable host check.

## Owner daily use

- **Off-LAN:** Tailscale on → companion `http://100.118.234.20` (or home-screen PWA).
- **On LAN:** desk `https://192.168.4.100/desk`, push via home-screen PWA.

## Verify on host

```bash
# copy owner token to readable path if needed
FS_CORP_TOKEN_FILE=/tmp/owner.token.exercise bash /opt/fs-corporation/scripts/verify_fs_dev_pilot.sh
```

## Next implementation

- GitHub pilot write (enroll disposable repo + first PR) — needs repo IDs in owner checklist.
- Android native handoff; dedicated worker host (optional).
- Furnished HQ room art deferred.
