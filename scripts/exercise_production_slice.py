#!/usr/bin/env python3
"""Run the suggested first production slice against a company DB.

Engineering mock draft → QC pass → CEO accept → Art/Marketing dispatch + drafts.
Optional: live GitHub open_pr for the same task id when --repo-id is set.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "config" / "departments.json").is_file():
    ROOT = Path(os.environ.get("FS_CORP_INSTALL_DIR", "/opt/fs-corporation"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from company.core import Company, now  # noqa: E402


def ensure_catalog(company: Company) -> None:
    if company.db.execute("SELECT 1 FROM departments LIMIT 1").fetchone():
        return
    company.seed_catalog(ROOT / "config" / "departments.json")


def ensure_project(company: Company, project_id: str, brief: str) -> None:
    if company.db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
        return
    company.enroll_project("human-ceo", project_id, brief)


def ensure_grants(company: Company, project_id: str) -> None:
    policy = company.policy()
    grants = dict(policy.get("grants") or {})
    expires = (now() + timedelta(days=365)).isoformat()
    needed = {
        "head": {
            "actions": ["draft", "prepare_pr"],
            "projects": [project_id],
            "budget_cents": 500_000,
            "per_action_cents": 50_000,
            "expires_at": expires,
            "requires_approval": [],
        },
        "art": {
            "actions": ["draft"],
            "projects": [project_id],
            "budget_cents": 50_000,
            "per_action_cents": 10_000,
            "expires_at": expires,
            "requires_approval": [],
        },
        "marketing": {
            "actions": ["draft"],
            "projects": [project_id],
            "budget_cents": 50_000,
            "per_action_cents": 10_000,
            "expires_at": expires,
            "requires_approval": [],
        },
    }
    changed = False
    for actor, grant in needed.items():
        existing = grants.get(actor)
        if not existing or project_id not in (existing.get("projects") or []):
            grants[actor] = grant
            changed = True
        elif actor in ("art", "marketing") and "draft" not in (existing.get("actions") or []):
            grants[actor] = grant
            changed = True
    if not changed:
        return
    body = {
        "version": policy["version"] + 1,
        "company_budget_cents": max(int(policy.get("company_budget_cents") or 0), 500_000),
        "grants": grants,
    }
    pid = company.propose_policy("human-ceo", body, "Production slice department grants")
    company.approve_policy("human-ceo", pid)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise Engineering→QC→accept→Art/Marketing slice")
    parser.add_argument("--db", default=os.environ.get("FS_CORP_DB", "/data/company.db"))
    parser.add_argument("--project", default="app")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--repo-id", default="", help="Optional enrolled GitHub repo id for live open_pr")
    parser.add_argument("--skip-github", action="store_true")
    args = parser.parse_args()
    stamp = int(time.time())
    eng_task = args.task_id or f"slice-eng-{stamp}"
    company = Company(args.db)
    report: dict = {"project": args.project, "engineering_task": eng_task}
    try:
        ensure_catalog(company)
        ensure_project(company, args.project, "Suggested first production slice")
        ensure_grants(company, args.project)

        if company.db.execute("SELECT 1 FROM completions WHERE project=?", (args.project,)).fetchone():
            print(json.dumps({
                "status": "skipped",
                "reason": f"project {args.project} already has an accepted completion",
            }, indent=2))
            return 0

        task = company.execute_mock(
            actor="head", project=args.project, action="draft", cost=25, task_id=eng_task)
        report["artifact_hash"] = task["artifact_hash"]
        report["engineering"] = {"status": task["status"]}

        github_row = None
        if args.repo_id and not args.skip_github:
            branch = f"company/{eng_task}"
            github_row = company.apply_github_effect(
                args.project, eng_task, "open_pr", str(args.repo_id), branch)
            report["github"] = {
                "status": github_row.get("status"),
                "remote_id": github_row.get("remote_id"),
                "branch": branch,
            }

        inspection = company.inspect_quality(
            "quality:Quality Inspector", eng_task, task["artifact_hash"], "pass")
        report["qc"] = inspection

        company.accept_project("human-ceo", eng_task, task["artifact_hash"])
        report["accepted"] = True

        company.activate_department_for_project(
            "human-ceo", args.project, "art")
        company.activate_department_for_project(
            "human-ceo", args.project, "marketing")
        dispatches = company.dispatch_project_brief(
            "human-ceo", args.project,
            brief="Add launch visuals and positioning for the accepted pilot deliverable",
            department_budgets={"art": 2_500, "marketing": 2_500},
            acceptance_criteria="Art asset + marketing brief recorded as mock drafts",
        )
        report["dispatches"] = dispatches

        art = company.execute_mock(
            actor="art", project=args.project, action="draft", cost=10,
            task_id=f"slice-art-{stamp}")
        mkt = company.execute_mock(
            actor="marketing", project=args.project, action="draft", cost=10,
            task_id=f"slice-mkt-{stamp}")
        report["art"] = {"task_id": art["id"], "status": art["status"]}
        report["marketing"] = {"task_id": mkt["id"], "status": mkt["status"]}
        report["status"] = "ok"
        print(json.dumps(report, indent=2, default=str))
        return 0
    finally:
        company.close()


if __name__ == "__main__":
    raise SystemExit(main())
