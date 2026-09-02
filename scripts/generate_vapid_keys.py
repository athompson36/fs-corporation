#!/usr/bin/env python3
"""Generate a VAPID key pair for Web Push. Writes PEM files under secrets/; never commit."""
from __future__ import annotations
import os
from pathlib import Path

from py_vapid import Vapid01


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "secrets"
    out_dir.mkdir(parents=True, exist_ok=True)
    public_path = out_dir / "vapid-public.pem"
    private_path = out_dir / "vapid-private.pem"
    vapid = Vapid01()
    vapid.generate_keys()
    vapid.save_public_key(str(public_path))
    vapid.save_key(str(private_path))
    os.chmod(private_path, 0o600)
    print("# Add to .env (gitignored) — paths are inside the API container (see docker-compose.yml mounts)")
    print("VAPID_PUBLIC_KEY_FILE=/run/secrets/vapid-public.pem")
    print("VAPID_PRIVATE_KEY_FILE=/run/secrets/vapid-private.pem")
    print("VAPID_CONTACT_EMAIL=mailto:owner@example.com")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
