"""Dispatch parameter key + mock/live recommendation (advisory only)."""
from __future__ import annotations
import json
import re
from pathlib import Path

from company.core import money
from company import model_provider

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

def _coerce_budget_cents(value) -> int:
    if isinstance(value, bool):
        raise ValueError("budget_cents must be an integer")
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != int(value):
            raise ValueError("budget_cents must be an integer")
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0
        numeric = stripped[1:] if stripped.startswith("+") else stripped
        if not numeric.isdigit():
            raise ValueError("budget_cents must be an integer")
        return int(numeric)
    raise ValueError("budget_cents must be an integer")

def validate_suggestion(raw: dict, catalog_ids: set[str], max_cents: int) -> dict:
    brief = str(raw.get("brief") or "").strip()
    criteria = str(raw.get("acceptance_criteria") or "").strip()
    if not brief or not criteria:
        raise ValueError("brief and acceptance_criteria required")
    departments_by_id: dict[str, dict] = {}
    dept_order: list[str] = []
    for item in raw.get("departments") or []:
        dept_id = str(item.get("id") or "").strip()
        if dept_id not in catalog_ids:
            continue
        amount = _coerce_budget_cents(item.get("budget_cents"))
        amount = money(max(0, min(amount, max_cents)))
        entry = {
            "id": dept_id,
            "budget_cents": amount,
            "recommended": bool(item.get("recommended", True)),
        }
        if dept_id in departments_by_id:
            dept_order.remove(dept_id)
        dept_order.append(dept_id)
        departments_by_id[dept_id] = entry
    departments = [departments_by_id[d] for d in dept_order]
    if not departments:
        raise ValueError("no valid departments")
    return {
        "brief": brief,
        "acceptance_criteria": criteria,
        "departments": departments,
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def model_registry_for_dispatch(company) -> dict:
    """File seed plus DB overlays (enabled flag from model_profiles)."""
    path = _repo_root() / "config" / "models.example.json"
    data = json.loads(path.read_text())
    profiles = dict(data.get("profiles") or {})
    for row in company.db.execute("SELECT id, body, enabled FROM model_profiles"):
        body = json.loads(row["body"])
        body["enabled"] = bool(row["enabled"])
        profiles[row["id"]] = body
    data["profiles"] = profiles
    return data


def _pick_live_profile(registry: dict) -> str | None:
    for profile_id, profile in (registry.get("profiles") or {}).items():
        if not profile.get("enabled"):
            continue
        if profile.get("provider") in model_provider.LIVE_PROVIDERS:
            return profile_id
    return None


def _parse_json_object(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("recommendation must be a JSON object")
    return data


def live_recommend(company, project_id: str) -> tuple[str, dict | None]:
    """Try live model recommend.

    Returns (status, payload) where status is ``ok``, ``unavailable``, or ``unusable``.
    """
    summary = model_provider.status_summary(probe=False)
    if not (summary.get("configured") and summary.get("live")):
        return "unavailable", None
    opts = build_dispatch_options(company, project_id)
    catalog_ids = {d["id"] for d in opts["departments"]}
    max_cents = opts["fields"]["department_budgets"]["max_cents"]
    registry = model_registry_for_dispatch(company)
    profile_id = _pick_live_profile(registry)
    if not profile_id:
        return "unavailable", None
    dept_lines = ", ".join(sorted(catalog_ids))
    prompt = (
        "Return JSON only (no markdown) with keys brief, acceptance_criteria, "
        "and departments (array of {id, budget_cents}). "
        f"Project id: {project_id}. Current brief: {opts['brief_default']!r}. "
        f"Allowed department ids: {dept_lines}. "
        f"budget_cents must be integers from 0 to {max_cents}. "
        "Recommend a small practical subset of departments."
    )
    try:
        result = company.invoke_model(profile_id, prompt, registry)
        parsed = _parse_json_object(result.get("text") or "")
        validated = validate_suggestion(parsed, catalog_ids, max_cents)
    except Exception:
        return "unusable", None
    return "ok", validated


def recommend_with_fallback(company, project_id: str, use_live: bool = True) -> dict:
    base = mock_recommend(company, project_id)
    if not use_live:
        return base
    status, live = live_recommend(company, project_id)
    if status == "ok" and live is not None:
        return {
            "source": "live",
            "live_attempted": True,
            "brief": live["brief"],
            "acceptance_criteria": live["acceptance_criteria"],
            "departments": live["departments"],
            "notes": [],
        }
    out = dict(base)
    out["live_attempted"] = True
    notes = list(out.get("notes") or [])
    note = "live_unusable" if status == "unusable" else "live_unavailable"
    if note not in notes:
        notes.append(note)
    out["notes"] = notes
    return out
