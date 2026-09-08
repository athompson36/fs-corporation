"""Durable finance: invoices, adjustments, budget-period closures (P3)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from company.core import money, now


def billed_gross_cents(company) -> int:
    return int(company.db.execute(
        "SELECT COALESCE(SUM(amount_cents),0) FROM billed_costs").fetchone()[0])


def billed_adjustment_cents(company) -> int:
    return int(company.db.execute(
        "SELECT COALESCE(SUM(amount_cents),0) FROM finance_adjustments").fetchone()[0])


def billed_net_cents(company) -> int:
    return billed_gross_cents(company) - billed_adjustment_cents(company)


def remaining_creditable(company, billed_cost_id: str) -> int:
    row = company.db.execute(
        "SELECT amount_cents FROM billed_costs WHERE id=?", (billed_cost_id,)
    ).fetchone()
    if not row:
        raise ValueError("Billed cost not found")
    used = company.db.execute(
        "SELECT COALESCE(SUM(amount_cents),0) FROM finance_adjustments WHERE billed_cost_id=?",
        (billed_cost_id,),
    ).fetchone()[0]
    return int(row["amount_cents"]) - int(used)


def list_billed_costs(
    company,
    *,
    limit: int = 100,
    include_fully_credited: bool = False,
) -> list[dict]:
    try:
        lim = int(limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be an integer") from exc
    if lim < 1:
        raise ValueError("limit must be >= 1")
    if lim > 500:
        lim = 500
    out: list[dict] = []
    for row in company.db.execute(
        "SELECT * FROM billed_costs ORDER BY recorded_at DESC"
    ):
        remaining = remaining_creditable(company, row["id"])
        if not include_fully_credited and remaining <= 0:
            continue
        out.append({
            "id": row["id"],
            "recorded_at": row["recorded_at"],
            "amount_cents": int(row["amount_cents"]),
            "remaining_creditable_cents": remaining,
            "provider": row["provider"],
            "profile_id": row["profile_id"],
            "source": row["source"],
            "task_id": row["task_id"],
        })
        if len(out) >= lim:
            break
    return out


def _parse_iso(stamp: str) -> str:
    if not isinstance(stamp, str) or not stamp.strip():
        raise ValueError("ISO timestamp required")
    # Validate parseable; store canonical string
    datetime.fromisoformat(stamp.strip().replace("Z", "+00:00"))
    return stamp.strip()


def create_invoice(company, actor: str, period_start: str, period_end: str) -> dict:
    company._ceo(actor)
    start = _parse_iso(period_start)
    end = _parse_iso(period_end)
    if start >= end:
        raise ValueError("period_start must be before period_end")
    rows = company.db.execute(
        """SELECT id, recorded_at, amount_cents, provider, profile_id
           FROM billed_costs
           WHERE recorded_at>=? AND recorded_at<?
           ORDER BY recorded_at, id""",
        (start, end),
    ).fetchall()
    lines = []
    for row in rows:
        remaining = remaining_creditable(company, row["id"])
        if remaining <= 0:
            continue
        # Invoice line uses original amount; voided rows excluded via remaining
        lines.append({
            "billed_cost_id": row["id"],
            "amount_cents": int(row["amount_cents"]),
            "recorded_at": row["recorded_at"],
            "provider": row["provider"],
            "profile_id": row["profile_id"],
        })
    if not lines:
        raise ValueError("Invoice window has no billable lines")
    total = sum(line["amount_cents"] for line in lines)
    iid = str(uuid.uuid4())
    body = {"lines": lines}
    with company.tx():
        company.db.execute(
            "INSERT INTO invoices VALUES(?,?,?,?,?,?,?,?,?)",
            (iid, now().isoformat(), actor, start, end, total, len(lines),
             json.dumps(body), "open"),
        )
        company._event(
            "invoice.created",
            {"id": iid, "total_cents": total, "line_count": len(lines)},
            actor_id=actor,
        )
    return get_invoice(company, iid)


def list_invoices(company) -> list[dict]:
    out = []
    for row in company.db.execute(
        "SELECT id, created_at, created_by, period_start, period_end, "
        "total_cents, line_count, status FROM invoices ORDER BY created_at DESC"
    ):
        out.append(dict(row))
    return out


def get_invoice(company, invoice_id: str) -> dict:
    row = company.db.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not row:
        raise ValueError("Invoice not found")
    data = dict(row)
    data["body"] = json.loads(data["body"])
    return data


def post_adjustment(
    company,
    actor: str,
    *,
    kind: str,
    billed_cost_id: str,
    reason: str,
    amount_cents: int | None = None,
    invoice_id: str | None = None,
) -> dict:
    company._ceo(actor)
    if kind not in {"void", "partial_credit"}:
        raise ValueError("kind must be void or partial_credit")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason required")
    if invoice_id:
        if not company.db.execute(
            "SELECT 1 FROM invoices WHERE id=?", (invoice_id,)
        ).fetchone():
            raise ValueError("Invoice not found")
    remaining = remaining_creditable(company, billed_cost_id)
    if remaining <= 0:
        raise PermissionError("Billed cost has no remaining creditable amount")
    if kind == "void":
        amount = remaining
    else:
        if amount_cents is None:
            raise ValueError("amount_cents required for partial_credit")
        amount = money(amount_cents)
        if amount <= 0 or amount > remaining:
            raise ValueError("partial_credit amount must be within remaining creditable")
    aid = str(uuid.uuid4())
    with company.tx():
        company.db.execute(
            "INSERT INTO finance_adjustments VALUES(?,?,?,?,?,?,?,?)",
            (aid, now().isoformat(), actor, kind, billed_cost_id, amount,
             reason.strip(), invoice_id),
        )
        event_kind = "finance.void" if kind == "void" else "finance.partial_credit"
        company._event(
            event_kind,
            {
                "id": aid,
                "billed_cost_id": billed_cost_id,
                "amount_cents": amount,
                "invoice_id": invoice_id,
            },
            actor_id=actor,
        )
    return dict(company.db.execute(
        "SELECT * FROM finance_adjustments WHERE id=?", (aid,)
    ).fetchone())


def list_adjustments(company) -> list[dict]:
    return [dict(r) for r in company.db.execute(
        "SELECT * FROM finance_adjustments ORDER BY created_at DESC, id")]


def finance_summary(company) -> dict:
    stamp = now().isoformat()
    period = company.db.execute(
        "SELECT * FROM budget_periods WHERE period_start<=? AND period_end>? LIMIT 1",
        (stamp, stamp),
    ).fetchone()
    open_period = None
    if period:
        closed = company.db.execute(
            "SELECT 1 FROM budget_period_closures WHERE budget_period_id=?",
            (period["id"],),
        ).fetchone()
        if not closed:
            open_period = dict(period)
    return {
        "billed_cost_gross_cents": billed_gross_cents(company),
        "billed_adjustment_cents": billed_adjustment_cents(company),
        "billed_cost_cents": billed_net_cents(company),
        "revenue_cents": int(company.db.execute(
            "SELECT COALESCE(SUM(amount_cents),0) FROM revenue").fetchone()[0]),
        "open_budget_period": open_period,
    }


def list_budget_periods(company) -> list[dict]:
    out = []
    for row in company.db.execute(
        "SELECT * FROM budget_periods ORDER BY period_start DESC"
    ):
        item = dict(row)
        closure = company.db.execute(
            "SELECT * FROM budget_period_closures WHERE budget_period_id=?",
            (row["id"],),
        ).fetchone()
        item["closed"] = closure is not None
        if closure:
            item["closure"] = {
                **dict(closure),
                "snapshot": json.loads(closure["snapshot"]),
            }
        out.append(item)
    return out


def close_budget_period(company, actor: str, period_id: str) -> dict:
    company._ceo(actor)
    period = company.db.execute(
        "SELECT * FROM budget_periods WHERE id=?", (period_id,)
    ).fetchone()
    if not period:
        raise ValueError("Budget period not found")
    if company.db.execute(
        "SELECT 1 FROM budget_period_closures WHERE budget_period_id=?",
        (period_id,),
    ).fetchone():
        raise PermissionError("Budget period already closed")
    snapshot = {
        "limit_cents": int(period["limit_cents"]),
        "period_start": period["period_start"],
        "period_end": period["period_end"],
        "scope": period["scope"],
        "simulated_spend_cents": int(company.db.execute(
            "SELECT COALESCE(SUM(cost),0) FROM ledger").fetchone()[0]),
        "billed_cost_gross_cents": billed_gross_cents(company),
        "billed_adjustment_cents": billed_adjustment_cents(company),
        "billed_cost_cents": billed_net_cents(company),
        "revenue_cents": int(company.db.execute(
            "SELECT COALESCE(SUM(amount_cents),0) FROM revenue").fetchone()[0]),
    }
    cid = str(uuid.uuid4())
    with company.tx():
        company.db.execute(
            "INSERT INTO budget_period_closures VALUES(?,?,?,?,?)",
            (cid, period_id, now().isoformat(), actor, json.dumps(snapshot)),
        )
        company._event(
            "budget.period_closed",
            {"id": cid, "budget_period_id": period_id, "snapshot": snapshot},
            actor_id=actor,
        )
    for item in list_budget_periods(company):
        if item["id"] == period_id:
            return item
    raise ValueError("Budget period not found after close")
