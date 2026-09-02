#!/usr/bin/env python3
"""Verify GitHub App credentials without printing secrets."""
from __future__ import annotations
import json
import sys

from company.github_app import github_configured, status_summary


def main() -> int:
    if not github_configured():
        print("GitHub App is not configured. Set GITHUB_APP_ID, GITHUB_INSTALLATION_ID, GITHUB_PRIVATE_KEY_FILE.")
        return 1
    summary = status_summary()
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("live") else 2


if __name__ == "__main__":
    raise SystemExit(main())
