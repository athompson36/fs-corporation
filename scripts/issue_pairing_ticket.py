#!/usr/bin/env python3
"""Issue a one-time companion pairing URL against the loopback API."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=os.environ.get("FS_CORP_API_BASE", "http://127.0.0.1:8000"))
    parser.add_argument("--token-file", default=os.environ.get("FS_CORP_TOKEN_FILE", ""))
    parser.add_argument(
        "--access-level",
        default="admin",
        choices=("read_only", "user", "admin"),
    )
    args = parser.parse_args()
    if not args.token_file:
        print("Set --token-file or FS_CORP_TOKEN_FILE", file=sys.stderr)
        return 1
    token = Path(args.token_file).read_text().strip()
    body = json.dumps({"payload": {"access_level": args.access_level}}).encode()
    req = urllib.request.Request(
        f"{args.base.rstrip('/')}/api/v1/remote-access/pairing",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"pair-cli-{os.getpid()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        return 1
    result = payload.get("result", payload)
    print(result.get("pair_url") or "")
    print(f"access_level={result.get('access_level') or args.access_level} expires={result.get('expires_at')}", file=sys.stderr)
    if not result.get("pair_url"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
