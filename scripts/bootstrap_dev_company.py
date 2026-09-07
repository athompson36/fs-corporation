#!/usr/bin/env python3
"""Idempotent dev bootstrap: catalog seed, default policy grants and project app."""
from __future__ import annotations
import os
from datetime import timedelta
from pathlib import Path

from company.core import Company, now

ROOT = Path(__file__).resolve().parents[1]


def bootstrap_dev(company: Company) -> None:
    catalog = ROOT / "config" / "departments.json"
    if catalog.is_file() and not company.db.execute("SELECT 1 FROM departments LIMIT 1").fetchone():
        company.seed_catalog(catalog)

    policy = company.policy()
    grants = dict(policy.get("grants") or {})
    expires = (now() + timedelta(days=365)).isoformat()
    changed = False
    if "head" not in grants:
        grants["head"] = {
            "actions": ["draft", "prepare_pr"],
            "projects": ["app"],
            "budget_cents": 500_000,
            "per_action_cents": 50_000,
            "expires_at": expires,
            "requires_approval": [],
        }
        changed = True
    for actor in ("art", "marketing"):
        if actor not in grants:
            grants[actor] = {
                "actions": ["draft"],
                "projects": ["app"],
                "budget_cents": 50_000,
                "per_action_cents": 10_000,
                "expires_at": expires,
                "requires_approval": [],
            }
            changed = True
    if changed:
        body = {
            "version": policy["version"] + 1,
            "company_budget_cents": max(int(policy.get("company_budget_cents") or 0), 500_000),
            "grants": grants,
        }
        pid = company.propose_policy("human-ceo", body, "Docker/fs-dev bootstrap grants")
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
