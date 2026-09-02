#!/usr/bin/env python3
"""Idempotent dev bootstrap: default policy grants and project app."""
from __future__ import annotations
import os
from datetime import timedelta

from company.core import Company, now


def bootstrap_dev(company: Company) -> None:
    policy = company.policy()
    grants = policy.get("grants") or {}
    if "head" not in grants:
        body = {
            "version": policy["version"] + 1,
            "company_budget_cents": 500_000,
            "grants": {
                "head": {
                    "actions": ["draft", "prepare_pr"],
                    "projects": ["app"],
                    "budget_cents": 500_000,
                    "per_action_cents": 50_000,
                    "expires_at": (now() + timedelta(days=365)).isoformat(),
                    "requires_approval": [],
                },
            },
        }
        pid = company.propose_policy("human-ceo", body, "Docker dev bootstrap grants")
        company.approve_policy("human-ceo", pid)
    if not company.db.execute("SELECT 1 FROM projects WHERE id=?", ("app",)).fetchone():
        company.enroll_project("human-ceo", "app", "Default dev project")


def main() -> None:
    company = Company(os.environ.get("FS_CORP_DB", "/data/company.db"))
    try:
        bootstrap_dev(company)
    finally:
        company.close()


if __name__ == "__main__":
    main()
