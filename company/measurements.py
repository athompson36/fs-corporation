"""Work-order baseline/after ops measurements (v0.3.87)."""
from __future__ import annotations

import json
import uuid

from company.core import now

METRIC_KEYS = (
    "accepted_artifacts",
    "open_tasks",
    "open_dispatches",
    "simulated_spend_cents",
    "billed_cost_cents",
)
TERMINAL_DISPATCH = frozenset({
    "accepted", "cancelled", "canceled", "closed", "completed", "failed", "rejected",
})
CLOSED_TASKS = frozenset({"accepted", "cancelled", "failed"})
_TERMINAL_SQL = ",".join(f"'{s}'" for s in sorted(TERMINAL_DISPATCH))
_CLOSED_TASKS_SQL = ",".join(f"'{s}'" for s in sorted(CLOSED_TASKS))


def capture_ops_metrics(company) -> dict:
    from company.finance import billed_net_cents

    accepted = company.db.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='accepted'").fetchone()[0]
    open_tasks = company.db.execute(
        f"SELECT COUNT(*) FROM tasks WHERE status NOT IN ({_CLOSED_TASKS_SQL})"
    ).fetchone()[0]
    open_dispatches = company.db.execute(
        f"SELECT COUNT(*) FROM project_dispatches WHERE status NOT IN ({_TERMINAL_SQL})"
    ).fetchone()[0]
    simulated_spend_cents = company.db.execute(
        "SELECT COALESCE(SUM(cost),0) FROM ledger").fetchone()[0]
    return {
        "accepted_artifacts": int(accepted),
        "open_tasks": int(open_tasks),
        "open_dispatches": int(open_dispatches),
        "simulated_spend_cents": int(simulated_spend_cents),
        "billed_cost_cents": int(billed_net_cents(company)),
    }


def _row(row) -> dict:
    return {
        "id": row["id"],
        "work_order_id": row["work_order_id"],
        "phase": row["phase"],
        "metrics": json.loads(row["metrics_json"]),
        "created_at": row["created_at"],
        "created_by": row["created_by"],
    }


def _insert_measurement(company, actor, work_order_id, phase, metrics) -> dict:
    rid = str(uuid.uuid4())
    stamp = now().isoformat()
    company.db.execute(
        "INSERT INTO work_order_measurements VALUES(?,?,?,?,?,?)",
        (rid, work_order_id, phase, json.dumps(metrics), stamp, actor),
    )
    company._event(
        f"work_order.measurement_{phase}",
        {"work_order_id": work_order_id, "metrics": metrics},
        actor_id=actor,
    )
    return dict(company.db.execute(
        "SELECT * FROM work_order_measurements WHERE id=?", (rid,)).fetchone())


def ensure_measurement(company, actor, work_order_id, phase: str) -> dict:
    assert phase in ("baseline", "after")
    if not company.db.execute("SELECT 1 FROM work_orders WHERE id=?", (work_order_id,)).fetchone():
        raise ValueError("Work order not found")
    existing = company.db.execute(
        "SELECT * FROM work_order_measurements WHERE work_order_id=? AND phase=?",
        (work_order_id, phase),
    ).fetchone()
    if existing:
        return _row(existing)
    metrics = capture_ops_metrics(company)
    depth = getattr(company, "_tx_depth", 0)
    if depth > 0:
        row = _insert_measurement(company, actor, work_order_id, phase, metrics)
    else:
        with company.tx():
            row = _insert_measurement(company, actor, work_order_id, phase, metrics)
    return _row(row)


def get_measurements(company, work_order_id) -> dict:
    baseline = after = None
    for row in company.db.execute(
        "SELECT * FROM work_order_measurements WHERE work_order_id=? ORDER BY phase",
        (work_order_id,),
    ):
        parsed = _row(row)
        if parsed["phase"] == "baseline":
            baseline = parsed
        elif parsed["phase"] == "after":
            after = parsed
    deltas = None
    if baseline and after:
        deltas = {
            k: after["metrics"][k] - baseline["metrics"][k]
            for k in METRIC_KEYS
        }
    return {
        "work_order_id": work_order_id,
        "baseline": baseline,
        "after": after,
        "deltas": deltas,
    }


def list_measurements(company, limit=50) -> list:
    rows = company.db.execute(
        """SELECT wo.id AS work_order_id, wo.payload, wo.status,
                  bm.created_at AS baseline_at, am.created_at AS after_at,
                  bm.metrics_json AS baseline_metrics, am.metrics_json AS after_metrics,
                  bm.created_by AS baseline_by, am.created_by AS after_by
           FROM work_orders wo
           LEFT JOIN work_order_measurements bm
             ON bm.work_order_id=wo.id AND bm.phase='baseline'
           LEFT JOIN work_order_measurements am
             ON am.work_order_id=wo.id AND am.phase='after'
           WHERE json_extract(wo.payload, '$.source') = 'consultant'
           ORDER BY COALESCE(bm.created_at, am.created_at, wo.id) DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    out = []
    for row in rows:
        payload = json.loads(row["payload"])
        baseline = after = deltas = None
        if row["baseline_metrics"]:
            baseline = {
                "metrics": json.loads(row["baseline_metrics"]),
                "created_at": row["baseline_at"],
                "created_by": row["baseline_by"],
            }
        if row["after_metrics"]:
            after = {
                "metrics": json.loads(row["after_metrics"]),
                "created_at": row["after_at"],
                "created_by": row["after_by"],
            }
        if baseline and after:
            deltas = {
                k: after["metrics"][k] - baseline["metrics"][k]
                for k in METRIC_KEYS
            }
        out.append({
            "work_order_id": row["work_order_id"],
            "proposal_id": payload.get("proposal_id"),
            "status": row["status"],
            "baseline": baseline,
            "after": after,
            "deltas": deltas,
        })
    return out
