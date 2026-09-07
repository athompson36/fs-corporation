#!/usr/bin/env python3
"""Exercise live GitHub apply_github_effect (open_pr or push) against enrolled pilot repo."""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from company.core import Company  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a live GitHub effect for pilot acceptance")
    parser.add_argument("--db", default=os.environ.get("FS_CORP_DB", "/data/company.db"))
    parser.add_argument("--project", default="app")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--operation", default="open_pr", choices=("open_pr", "push", "prepare_pr", "merge"))
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--branch", default="")
    parser.add_argument("--pr-number", default="", help="Required for merge unless a prior open_pr effect exists for the task")
    args = parser.parse_args()
    task_id = args.task_id or f"github-pilot-{int(__import__('time').time())}"
    branch = args.branch or f"company/{task_id}"
    company = Company(args.db)
    try:
        kwargs = {}
        if args.pr_number:
            kwargs["pr_number"] = args.pr_number
        row = company.apply_github_effect(
            args.project, task_id, args.operation, args.repo_id, branch, **kwargs)
        print(json.dumps(dict(row), indent=2, default=str))
        return 0 if row.get("status") == "applied" else 1
    finally:
        company.close()


if __name__ == "__main__":
    raise SystemExit(main())
