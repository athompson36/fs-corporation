#!/usr/bin/env python3
"""Verify live VAPID delivery path (applied or failed, not live_unavailable)."""
from __future__ import annotations
import json
import os
import sys

from company.core import Company
from company.push_vapid import status_summary, vapid_configured


def main() -> int:
    if not vapid_configured():
        print("VAPID not configured. Set VAPID_* in .env or secrets.")
        return 1
    print(json.dumps(status_summary(), indent=2))
    db = os.environ.get("FS_CORP_DB", "/data/company.db")
    company = Company(db)
    try:
        endpoint = "https://push.example.test/fs-corp-verify"
        sub = company.register_push_subscription(
            "human-ceo", endpoint, {"p256dh": "verify", "auth": "verify"})
        token = f"verify-{sub['id'][:8]}"
        result = company.notify_push("owner_inbox", f"Push delivery verify {token}", {"request_id": token})
        delivery = result["deliveries"][0]
        out = {
            "subscription_id": sub["id"],
            "delivery_status": delivery["status"],
            "delivery_id": delivery["id"],
        }
        print(json.dumps(out, indent=2))
        if delivery["status"] == "live_unavailable":
            return 2
        # failed = live send attempted (fake endpoint); applied = real browser endpoint
        return 0
    finally:
        company.close()


if __name__ == "__main__":
    raise SystemExit(main())
