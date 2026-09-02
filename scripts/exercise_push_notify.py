#!/usr/bin/env python3
"""Send a CEO test Web Push via the loopback API (requires active subscription + VAPID)."""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def api(base: str, method: str, path: str, token: str, payload: dict | None = None, idem: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if method != "GET":
        headers["Content-Type"] = "application/json"
        if idem:
            headers["Idempotency-Key"] = idem
        data = json.dumps({"payload": payload or {}}).encode()
    req = urllib.request.Request(f"{base.rstrip('/')}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
        return body.get("result", body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a test Web Push notification")
    parser.add_argument("--base", default=os.environ.get("FS_CORP_API_BASE", "http://localhost:8013"))
    parser.add_argument("--token-file", default=os.environ.get("FS_CORP_TOKEN_FILE", ""))
    parser.add_argument("--subject", default="")
    args = parser.parse_args()
    if not args.token_file:
        print("Set --token-file or FS_CORP_TOKEN_FILE", file=sys.stderr)
        return 1
    token = Path(args.token_file).read_text().strip()
    subject = args.subject.strip() or f"Push test {int(time.time())}"
    try:
        status = api(args.base, "GET", "/api/v1/push/status", token)
        print("status:", json.dumps(status, indent=2))
        if not status.get("live"):
            print("VAPID not live; configure keys first.", file=sys.stderr)
            return 2
        subs = api(args.base, "GET", "/api/v1/push/subscriptions", token)
        active = (subs.get("subscriptions") if isinstance(subs, dict) else None) or []
        print(f"active_subscriptions: {len(active)}")
        if not active:
            print("No active push subscriptions. Open the companion on HTTPS and allow notifications.", file=sys.stderr)
            return 3
        result = api(
            args.base, "POST", "/api/v1/push/notify", token,
            {"kind": "owner_inbox", "subject": subject, "test": True},
            idem=f"push-test-{int(time.time())}",
        )
        print("notify:", json.dumps(result, indent=2))
        deliveries = result.get("deliveries") or []
        if not deliveries:
            return 4
        statuses = {d.get("status") for d in deliveries}
        if "live_unavailable" in statuses and statuses <= {"live_unavailable"}:
            print("VAPID path unavailable (live_unavailable).", file=sys.stderr)
            return 2
        # applied = browser got it; failed = live send attempted (e.g. stale/fake endpoint)
        if statuses & {"applied", "failed"}:
            return 0
        return 6
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
