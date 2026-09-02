#!/usr/bin/env python3
"""Verify VAPID Web Push configuration without sending notifications."""
from __future__ import annotations
import json
import sys

from company.push_vapid import status_summary, vapid_configured


def main() -> int:
    if not vapid_configured():
        print("VAPID not configured. Set VAPID_PRIVATE_KEY or VAPID_PRIVATE_KEY_FILE.")
        return 1
    summary = status_summary()
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("live") else 2


if __name__ == "__main__":
    raise SystemExit(main())
