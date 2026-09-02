#!/usr/bin/env python3
"""Approve and poll a live RSS/Atom feed via the loopback API."""
from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def api(base: str, method: str, path: str, token: str, payload: dict | None = None, idem: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if idem:
        headers["Idempotency-Key"] = idem
    body = {"payload": payload or {}}
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{base.rstrip('/')}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        response = json.loads(resp.read().decode())
        return response.get("result", response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve and poll a market feed")
    parser.add_argument("--base", default=os.environ.get("FS_CORP_API_BASE", "http://localhost:8013"))
    parser.add_argument("--token-file", default=os.environ.get("FS_CORP_TOKEN_FILE", ""))
    parser.add_argument("--feed-id", default="github-blog")
    parser.add_argument("--url", default="https://github.blog/feed/")
    args = parser.parse_args()
    if not args.token_file:
        print("Set --token-file or FS_CORP_TOKEN_FILE", file=sys.stderr)
        return 1
    token = Path(args.token_file).read_text().strip()
    fid = args.feed_id
    try:
        api(args.base, "POST", "/api/v1/feeds", token, {"id": fid, "url": args.url}, idem=f"feed-{fid}")
        print(f"approved feed {fid}")
        polled = api(args.base, "POST", f"/api/v1/feeds/{fid}/poll", token, idem=f"poll-{fid}")
        print("poll:", json.dumps(polled, indent=2))
        status = polled.get("status")
        ingested = polled.get("ingested", 0)
        return 0 if status == "applied" and ingested > 0 else 2
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
