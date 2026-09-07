#!/usr/bin/env python3
"""Exercise path-scoped Funnel webhook URL: signed ping via public_url from github/status."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _token(path: str | None, explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    if path:
        return Path(path).expanduser().read_text().strip()
    env = os.environ.get("FS_CORP_TOKEN") or os.environ.get("FS_CORP_OWNER_TOKEN")
    if env:
        return env.strip()
    raise SystemExit("Need --token, --token-file, or FS_CORP_TOKEN")


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default=os.environ.get("FS_CORP_API_BASE", "http://192.168.4.100"))
    p.add_argument("--token-file", default=os.environ.get("FS_CORP_TOKEN_FILE"))
    p.add_argument("--token", default=None)
    p.add_argument("--secret", default=os.environ.get("GITHUB_WEBHOOK_SECRET"),
                   help="HMAC secret (default: GITHUB_WEBHOOK_SECRET env)")
    p.add_argument("--secret-file", default=None, help="File containing webhook secret")
    args = p.parse_args()
    token = _token(args.token_file, args.token)
    base = args.base.rstrip("/")
    status = _get(f"{base}/api/v1/github/status", token)
    funnel = status.get("funnel_webhooks") or {}
    print(json.dumps({"github": {
        "live": status.get("live"),
        "webhook_secret_configured": status.get("webhook_secret_configured"),
        "funnel_webhooks": funnel,
    }}, indent=2))
    if not funnel.get("opt_in"):
        print("FAIL: funnel not opted in (FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS!=1)", file=sys.stderr)
        return 2
    public = funnel.get("public_url")
    if not public:
        print("FAIL: no public_url — run funnel apply / enable Tailscale Funnel ACL", file=sys.stderr)
        return 3
    secret = args.secret
    if args.secret_file:
        secret = Path(args.secret_file).expanduser().read_text().strip()
    if not secret:
        # Fall back to local .env without printing it
        env_path = Path(__file__).resolve().parents[1] / ".env"
        if env_path.is_file():
            for line in env_path.read_text().splitlines():
                if line.startswith("GITHUB_WEBHOOK_SECRET="):
                    secret = line.split("=", 1)[1].strip().strip("'\"")
                    break
    if not secret:
        print("FAIL: need GITHUB_WEBHOOK_SECRET to sign ping", file=sys.stderr)
        return 4
    body = json.dumps({"zen": "fs-corp-funnel-ping", "hook_id": 0}).encode()
    delivery = f"funnel-ex-{int(time.time())}"
    req = urllib.request.Request(
        public,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": delivery,
            "X-Hub-Signature-256": _sign(secret, body),
            "User-Agent": "FS-Corporation-Funnel-Exercise/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode()
            code = resp.status
    except urllib.error.HTTPError as exc:
        print(f"FAIL: HTTP {exc.code} from {public}: {exc.read()[:500]!r}", file=sys.stderr)
        return 5
    except urllib.error.URLError as exc:
        print(f"FAIL: unreachable {public}: {exc}", file=sys.stderr)
        return 6
    print(json.dumps({"post": {"url": public, "status": code, "body": json.loads(raw) if raw else {}}}, indent=2))
    data = json.loads(raw) if raw else {}
    if code != 200 or data.get("status") not in {"accepted", "duplicate"}:
        print("FAIL: unexpected webhook response", file=sys.stderr)
        return 7
    print("OK: Funnel webhook path accepted signed ping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
