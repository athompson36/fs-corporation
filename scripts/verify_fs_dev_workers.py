#!/usr/bin/env python3
"""Verify fs-dev container worker prerequisites without dispatching tasks."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from company.worker_status import status_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-plane",
        action="store_true",
        help="exit 3 when worker_plane is not healthy (default: warn only)",
    )
    args = parser.parse_args(argv)
    summary = status_summary()
    print(json.dumps(summary, indent=2))
    plane = summary.get("worker_plane") or {}
    if plane.get("state") != "healthy":
        print(
            f"warning: worker_plane state={plane.get('state')} reasons={plane.get('reasons')}",
            file=sys.stderr,
        )
        if args.require_plane:
            return 3
    return 0 if summary.get("container_dispatch_ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
