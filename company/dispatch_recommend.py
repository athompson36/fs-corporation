"""Dispatch parameter key + mock/live recommendation (advisory only)."""
from __future__ import annotations
import re
from company.core import money

BUDGET_PRESETS_CENTS = (100, 300, 500, 1000, 5000)

BRIEF_TEMPLATES = [
    {"id": "ship-feature", "label": "Ship feature with tests",
     "body": "Deliver the next scoped feature for this project with automated coverage."},
    {"id": "bugfix", "label": "Bugfix with repro",
     "body": "Reproduce, fix, and verify the reported defect; include regression coverage."},
    {"id": "ops-hardening", "label": "Ops hardening",
     "body": "Harden deploy, monitoring, or recovery for this project without expanding product scope."},
]

CRITERIA_TEMPLATES = [
    {"id": "tests-qc", "label": "Tests + QC gate",
     "body": "Automated tests green; QC inspect passes; acceptance recorded."},
    {"id": "docs-only", "label": "Docs evidence",
     "body": "Documented change with linked evidence artifact."},
]

def remaining_budget_cents(company) -> int:
    policy = company.policy()
    company_budget = money(policy["company_budget_cents"])
    spent = company.db.execute("SELECT COALESCE(SUM(cost),0) FROM ledger").fetchone()[0]
    reserved = company.db.execute(
        "SELECT COALESCE(SUM(amount_cents),0) FROM reservations WHERE status='reserved'"
    ).fetchone()[0]
    return max(0, company_budget - int(spent) - int(reserved))

def build_dispatch_options(company, project_id: str) -> dict:
    row = company.db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        raise ValueError("Project not found")
    max_cents = remaining_budget_cents(company)
    departments = []
    for dept in company.list_org()["departments"]:
        dispatchable = company.department_dispatchable(project_id, dept["id"])
        seat = dept.get("seat") or {}
        seat_status = seat.get("status") or "vacant"
        status = "active" if dispatchable else "dormant"
        departments.append({
            "id": dept["id"],
            "name": dept["name"],
            "status": status,
            "dispatchable": dispatchable,
            "seat_status": seat_status,
            "principal_id": seat.get("principal_id"),
        })
    return {
        "project_id": project_id,
        "brief_default": row["brief"],
        "fields": {
            "brief": {"kind": "text_with_templates", "required": True, "templates": list(BRIEF_TEMPLATES)},
            "acceptance_criteria": {
                "kind": "text_with_templates", "required": True, "templates": list(CRITERIA_TEMPLATES),
            },
            "department_budgets": {
                "kind": "cents_map", "required": True, "min_cents": 0, "max_cents": max_cents,
                "presets_cents": list(BUDGET_PRESETS_CENTS), "unit": "USD_cents",
                "max_basis": "company_budget_cents minus simulated spend and open reservations",
            },
            "due_at": {"kind": "datetime_optional", "required": False, "format": "ISO-8601"},
        },
        "departments": departments,
    }

def _keyword_departments(brief: str) -> list[str]:
    text = (brief or "").lower()
    chosen: list[str] = []
    def add(dept):
        if dept not in chosen:
            chosen.append(dept)
    if re.search(r"\b(code|app|api|repo|bug|fix)\b", text):
        add("engineering"); add("product")
    if re.search(r"\b(test|tests|qc|quality|acceptance)\b", text):
        add("quality")
    if re.search(r"\b(design|art|ui|brand)\b", text):
        add("art")
    if re.search(r"\b(launch|marketing|campaign)\b", text):
        add("marketing")
    if not chosen:
        add("engineering")
    return chosen

def _split_budgets(dept_ids: list[str], max_cents: int) -> dict[str, int]:
    if not dept_ids or max_cents <= 0:
        return {d: 0 for d in dept_ids}
    # Prefer documented example split when possible; otherwise equal presets.
    preferred = {"engineering": 300, "product": 200, "quality": 100, "art": 100, "marketing": 100}
    out = {}
    remaining = max_cents
    for d in dept_ids:
        want = preferred.get(d, 100)
        pick = 0
        for p in sorted(BUDGET_PRESETS_CENTS, reverse=True):
            if p <= want and p <= remaining:
                pick = p
                break
        if pick == 0 and remaining > 0:
            pick = min(remaining, BUDGET_PRESETS_CENTS[0])
        out[d] = pick
        remaining -= pick
    return out

def mock_recommend(company, project_id: str) -> dict:
    opts = build_dispatch_options(company, project_id)
    max_cents = opts["fields"]["department_budgets"]["max_cents"]
    brief_default = opts["brief_default"]
    dept_ids = _keyword_departments(brief_default)
    # Keep only catalog ids
    catalog = {d["id"] for d in opts["departments"]}
    dept_ids = [d for d in dept_ids if d in catalog]
    budgets = _split_budgets(dept_ids, max_cents)
    return {
        "source": "mock",
        "live_attempted": False,
        "brief": f"Ship {project_id}: {brief_default}",
        "acceptance_criteria": (
            f"{CRITERIA_TEMPLATES[0]['body']} Recorded for {project_id}."
        ),
        "departments": [
            {"id": d, "budget_cents": budgets[d], "recommended": True} for d in dept_ids
        ],
        "notes": [],
    }

def validate_suggestion(raw: dict, catalog_ids: set[str], max_cents: int) -> dict:
    brief = str(raw.get("brief") or "").strip()
    criteria = str(raw.get("acceptance_criteria") or "").strip()
    if not brief or not criteria:
        raise ValueError("brief and acceptance_criteria required")
    departments = []
    for item in raw.get("departments") or []:
        dept_id = str(item.get("id") or "").strip()
        if dept_id not in catalog_ids:
            continue
        amount = money(int(item.get("budget_cents") or 0))
        amount = max(0, min(amount, max_cents))
        departments.append({
            "id": dept_id,
            "budget_cents": amount,
            "recommended": bool(item.get("recommended", True)),
        })
    if not departments:
        raise ValueError("no valid departments")
    return {
        "brief": brief,
        "acceptance_criteria": criteria,
        "departments": departments,
    }
