#!/usr/bin/env python3
"""Verify fs-dev container worker prerequisites without dispatching tasks."""
from __future__ import annotations
import json
import sys

from company.worker_status import status_summary


def main() -> int:
    summary = status_summary()
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("container_dispatch_ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
