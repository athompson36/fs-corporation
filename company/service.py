"""Loopback control service. Not a trusted remote API."""
from __future__ import annotations
import argparse
import asyncio
import json
import tempfile
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from company import __version__
from company.core import Company, canonical, digest
from company.consultant import ConsultantDesk

DEFAULT_DATA_DIR = ".local"
DEFAULT_DB = ".local/company.db"
DEFAULT_TOKEN_FILE = ".local/owner.token"

DESK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>FS-Corporation — CEO desk</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
:root { color-scheme: dark; }
body { font-family: system-ui, sans-serif; background:#111; color:#eee; margin:0; }
main { max-width: 52rem; margin: 0 auto; padding: 1rem; }
nav a { color:#9cf; margin-right:1rem; }
section { border:1px solid #444; padding:1rem; margin:1rem 0; }
.muted { color:#bbb; }
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
</head>
<body>
<main>
<nav aria-label="Primary">
<a href="#desk">CEO desk</a>
<a href="#hq">Headquarters</a>
<a href="#decisions">Decisions</a>
<a href="#consultant">Consultant</a>
</nav>
<h1 id="desk">CEO desk</h1>
<p class="muted">Reads persisted company state. Occupancy is not running-model count.</p>
<section id="status"><h2>Status</h2><pre id="status-json">Loading…</pre></section>
<section id="decisions"><h2>Policy proposals</h2><ul id="proposal-list"></ul></section>
<section id="consultant"><h2>Consultant inbox</h2><ul id="consultant-list"></ul></section>
<section id="hq"><h2>Headquarters</h2>
<p>List navigation of rooms from expansion events.</p>
<ul id="room-list"></ul>
<svg id="floor" viewBox="0 0 200 80" role="img" aria-label="2D floor plan of provisioned rooms">
</svg>
</section>
</main>
<script>
async function load() {
  const headers = {Authorization: 'Bearer ' + (localStorage.getItem('ownerToken')||'')};
  const status = await fetch('/api/v1/company', {headers});
  document.getElementById('status-json').textContent = await status.text();
  const hq = await fetch('/api/v1/headquarters', {headers});
  const data = await hq.json();
  const list = document.getElementById('room-list');
  list.innerHTML = '';
  (data.rooms||[]).forEach(room => {
    const li = document.createElement('li');
    li.textContent = room.id + ' — ' + room.status + ' — ' + room.source_project;
    list.appendChild(li);
  });
  const cons = await fetch('/api/v1/consultant-proposals', {headers});
  const cj = await cons.json();
  const cl = document.getElementById('consultant-list');
  cl.innerHTML = '';
  (cj.proposals||[]).forEach(p => {
    const li = document.createElement('li');
    const title = (p.body && p.body.title) ? p.body.title : p.id;
    li.textContent = title + ' — ' + p.status;
    cl.appendChild(li);
  });
  const ev = await fetch('/api/v1/events?limit=20', {headers});
  const ej = await ev.json();
  const pl = document.getElementById('proposal-list');
  pl.innerHTML = '';
  (ej.items||[]).forEach(item => {
    const li = document.createElement('li');
    li.textContent = item.kind + ' @ ' + item.at;
    pl.appendChild(li);
  });
  const svg = document.getElementById('floor');
  svg.innerHTML = '';
  (data.rooms||[]).forEach((room, i) => {
    const x = 10 + (i % 4) * 48;
    const y = 10 + Math.floor(i / 4) * 36;
    const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    r.setAttribute('x', x); r.setAttribute('y', y);
    r.setAttribute('width', 40); r.setAttribute('height', 28);
    r.setAttribute('fill', room.status === 'built' ? '#356' : '#333');
    r.setAttribute('stroke', '#888');
    svg.appendChild(r);
    const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('x', x+4); t.setAttribute('y', y+16); t.setAttribute('fill', '#eee');
    t.setAttribute('font-size', '6');
    t.textContent = room.status;
    svg.appendChild(t);
  });
}
load().catch(err => { document.getElementById('status-json').textContent = String(err); });
</script>
</body>
</html>
"""


class Command(BaseModel):
    expected_policy_version: int | None = None
    payload: dict = Field(default_factory=dict)


def _json(data, code=200):
    return JSONResponse(status_code=code, content=data)


def create_app(company: Company) -> FastAPI:
    app = FastAPI(title="FS-Corporation", version=__version__)
    app.state.company = company
    desk = ConsultantDesk(company)

    def principal(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="unauthenticated")
        ident = company.identity_for_token(authorization.split(" ", 1)[1].strip())
        if not ident:
            raise HTTPException(status_code=401, detail="unauthenticated")
        return ident

    def scoped(ident, scope):
        try:
            company.require_scope(ident, scope)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    def envelope(ident, body: Command):
        if body.expected_policy_version is not None and body.expected_policy_version != company.policy()["version"]:
            raise HTTPException(status_code=409, detail="Stale policy version")
        payload = dict(body.payload or {})
        payload.pop("actor", None)
        return payload

    def run(ident, key: str | None, payload: dict, handler):
        req_hash = digest({"payload": payload})
        if key:
            existing = company.lookup_command(key)
            if existing:
                if existing["request_hash"] != req_hash:
                    raise HTTPException(status_code=409, detail="Idempotency key reused with different payload")
                return _json(json.loads(existing["response_body"]), existing["status_code"])
        try:
            result, code = handler()
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            text = str(exc)
            if "Stale" in text or "stale" in text or "rebase" in text:
                raise HTTPException(status_code=409, detail=text) from exc
            raise HTTPException(status_code=422, detail=text) from exc
        wrapped = {
            "operation_id": digest({"result": result, "principal": ident["principal_id"]})[:16],
            "resource_version": company.policy()["version"],
            "status": "ok" if code < 300 else "error",
            "event_correlation_id": wrapped_corr(result),
            "result": result,
        }
        if key:
            company.remember_command(key, ident["principal_id"], req_hash, code, json.dumps(wrapped))
        return _json(wrapped, code)

    def wrapped_corr(result):
        if isinstance(result, dict):
            return result.get("id") or result.get("task_id") or result.get("event_correlation_id")
        return None

    @app.get("/", response_class=HTMLResponse)
    def desk_page():
        return DESK_HTML

    @app.get("/api/v1/health")
    def health():
        return {"ok": True, "version": app.version, "db": company.db_path}

    @app.get("/api/v1/company")
    def get_company(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.status() | {"paused": company.db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0]}

    @app.post("/api/v1/company/pause")
    def pause(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (company.pause(ident["principal_id"]) or {"paused": True}, 200))

    @app.post("/api/v1/company/resume")
    def resume(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.resume")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (company.pause(ident["principal_id"], False) or {"paused": False}, 200))

    @app.get("/api/v1/departments")
    def departments(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        rows = [dict(r) for r in company.db.execute("SELECT id,name,head_title,initially_active FROM departments ORDER BY id")]
        return {"departments": rows}

    @app.post("/api/v1/delegations")
    def delegations(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "delegation.propose")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: ({"id": company.create_delegation(ident["principal_id"], **payload)}, 200))

    @app.post("/api/v1/delegations/{did}/revoke")
    def revoke(did: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "delegation.revoke")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"id": did}, lambda: (company.revoke_delegation(ident["principal_id"], did) or {"id": did, "status": "revoked"}, 200))

    @app.post("/api/v1/policy-proposals")
    def propose(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "policy.propose")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: ({"id": company.propose_policy(ident["principal_id"], payload["policy"], payload.get("reason", "api"))}, 200))

    @app.post("/api/v1/policy-proposals/{pid}/decision")
    def policy_decision(pid: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "policy.approve")
        payload = envelope(ident, body)
        decision = payload.get("decision", "approved")
        def go():
            if decision == "approved":
                company.approve_policy(ident["principal_id"], pid)
            elif decision == "rejected":
                company.reject_policy(ident["principal_id"], pid, payload.get("reason", "rejected"))
            elif decision == "withdrawn":
                company.withdraw_policy(ident["principal_id"], pid)
            else:
                raise ValueError("Unknown decision")
            return {"id": pid, "decision": decision}, 200
        return run(ident, idempotency_key, payload | {"id": pid}, go)

    @app.get("/api/v1/policy-proposals/{pid}/diff")
    def policy_diff(pid: str, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "policy.propose")
        try:
            return company.policy_diff(pid)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/policy/rollback")
    def rollback(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "policy.approve")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: ({"version": company.rollback_policy(ident["principal_id"], payload["target_version"], payload.get("reason", "rollback"))}, 200))

    @app.get("/api/v1/dashboard")
    def dashboard(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.ceo_dashboard()

    @app.get("/api/v1/projects")
    def list_projects(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return {"projects": company.list_projects()}

    @app.get("/api/v1/projects/{project_id}")
    def get_project(project_id: str, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        try:
            return company.project_detail(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/decisions/inbox")
    def decisions_inbox(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.decisions_inbox()

    @app.get("/api/v1/owner-inbox")
    def owner_inbox(status: str | None = None, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        try:
            return company.owner_inbox(status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/owner-inbox")
    def owner_inbox_create(body: Command, authorization: str | None = Header(default=None),
                            idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "owner.escalate")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (company.create_owner_request(
            ident["principal_id"], payload["department_id"], payload["kind"],
            payload["subject"], payload["body"], payload.get("project_id")), 200))

    @app.post("/api/v1/push/subscriptions")
    def push_register(body: Command, authorization: str | None = Header(default=None),
                      idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (
            company.register_push_subscription(ident["principal_id"], payload["endpoint"], payload.get("keys")), 200))

    @app.post("/api/v1/push/subscriptions/{subscription_id}/revoke")
    def push_revoke(subscription_id: str, body: Command, authorization: str | None = Header(default=None),
                    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"id": subscription_id}, lambda: (
            company.revoke_push_subscription(ident["principal_id"], subscription_id), 200))

    @app.post("/api/v1/owner-inbox/{request_id}/respond")
    def owner_inbox_respond(request_id: str, body: Command, authorization: str | None = Header(default=None),
                              idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"id": request_id}, lambda: (
            company.respond_owner_request(ident["principal_id"], request_id, payload["response"],
                                          payload.get("close", True)), 200))

    @app.post("/api/v1/projects/{project_id}/dispatch-brief")
    def dispatch_brief(project_id: str, body: Command, authorization: str | None = Header(default=None),
                       idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "project.enroll")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"project_id": project_id}, lambda: (
            {"dispatches": company.dispatch_project_brief(
                ident["principal_id"], project_id, payload["brief"], payload["departments"],
                payload["acceptance_criteria"], payload["budget_cents"], payload.get("due_at"))}, 200))

    @app.get("/api/v1/events/stream")
    async def events_stream(cursor: int = 0, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "audit.read")

        async def generate():
            pos = cursor
            while True:
                page = company.events_page(pos, 20)
                for item in page["items"]:
                    pos = item["seq"]
                    yield f"data: {json.dumps({'seq': item['seq'], 'kind': item['kind'], 'at': item['at']})}\n\n"
                if not page["items"]:
                    await asyncio.sleep(1)
                if len(page["items"]) < 20:
                    await asyncio.sleep(1)

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.post("/api/v1/projects")
    def projects(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "project.enroll")
        payload = envelope(ident, body)
        def go():
            if payload.get("platform") or payload.get("domain") == "hardware":
                return company.enroll_hardware_project(
                    ident["principal_id"], payload["id"], payload.get("brief", "enrolled"),
                    payload.get("platform", "generic-sbc"), payload.get("classification", "internal")), 200
            return {"id": company.enroll_project(ident["principal_id"], payload["id"], payload.get("brief", "enrolled"), payload.get("classification", "internal"))}, 200
        return run(ident, idempotency_key, payload, go)

    @app.post("/api/v1/projects/{project_id}/tasks")
    def create_task(project_id: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "task.create")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"project_id": project_id}, lambda: (dict(company.queue_task(ident["principal_id"], project_id, payload["action"], payload["cost"], payload["task_id"])), 200))

    @app.post("/api/v1/tasks/{task_id}/dispatch")
    def dispatch(task_id: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "task.dispatch")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"task_id": task_id}, lambda: (dict(company.dispatch_queued(task_id, payload.get("approval"))), 200))

    @app.post("/api/v1/tasks/{task_id}/dispatch-worker")
    def dispatch_worker(task_id: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "task.dispatch")
        payload = envelope(ident, body)
        worker_id = payload.get("worker_id") or ident["principal_id"]
        scratch = payload.get("scratch_root") or tempfile.mkdtemp(prefix="company-worker-")
        runtime = payload.get("runtime", "subprocess")
        return run(ident, idempotency_key, payload | {"task_id": task_id}, lambda: (
            dict(company.dispatch_queued_isolated(worker_id, task_id, scratch, payload.get("approval"), runtime=runtime)), 200))

    @app.post("/api/v1/tasks/{task_id}/accept")
    def accept(task_id: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "artifact.accept")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"task_id": task_id}, lambda: (company.accept_project(ident["principal_id"], task_id, payload["artifact_hash"]) or {"task_id": task_id, "status": "accepted"}, 200))

    @app.post("/api/v1/tasks/{task_id}/quality-inspect")
    def quality_inspect(task_id: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "quality.inspect")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"task_id": task_id}, lambda: (company.inspect_quality(
            ident["principal_id"], task_id, payload["artifact_hash"], payload["verdict"]), 200))

    @app.get("/api/v1/hr/development")
    def hr_development(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        try:
            return company.development_roster(ident["principal_id"])
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.post("/api/v1/employees")
    def hire(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (company.hire_employee(
            ident["principal_id"], payload["id"], payload["position_id"], payload["display_name"],
            payload.get("attributes") or {}, payload["background"]), 200))

    @app.get("/api/v1/employees/{employee_id}")
    def get_employee(employee_id: str, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        try:
            company._hr_or_ceo(ident["principal_id"])
            return company.employee(employee_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/employees/{employee_id}/training")
    def employee_training(employee_id: str, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        try:
            return company.training_file(ident["principal_id"], employee_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/training/schedule")
    def schedule_training(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: ({"training": company.schedule_company_training(ident["principal_id"])}, 200))

    @app.post("/api/v1/employees/{employee_id}/goals")
    def set_goal(employee_id: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"employee_id": employee_id}, lambda: (company.set_performance_goal(
            ident["principal_id"], employee_id, payload["title"], payload["target"], payload["period"]), 200))

    @app.post("/api/v1/employees/{employee_id}/reviews")
    def review_employee(employee_id: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"employee_id": employee_id}, lambda: (company.record_performance_review(
            ident["principal_id"], employee_id, payload["score"], payload["notes"]), 200))

    @app.get("/api/v1/employees/{employee_id}/performance")
    def employee_performance(employee_id: str, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        try:
            return company.performance_trend(ident["principal_id"], employee_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/model-assignments")
    def models(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "model.assign")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: ({"id": company.assign_model(ident["principal_id"], payload["scope_kind"], payload["scope_id"], payload["profile_id"])}, 200))

    @app.post("/api/v1/signals")
    def signals(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "intelligence.ingest")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: ({"id": company.ingest_signal(**payload)}, 200))

    @app.post("/api/v1/expansions")
    def expansions(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "facilities.propose")
        payload = envelope(ident, body)
        def go():
            company.cost_expansion(ident["principal_id"], payload["id"], payload.get("estimate_cents", 0))
            return {"id": payload["id"], "status": "costed"}, 200
        return run(ident, idempotency_key, payload, go)

    @app.post("/api/v1/expansions/{eid}/decision")
    def expansion_decision(eid: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "facilities.approve")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"id": eid}, lambda: (company.approve_expansion(ident["principal_id"], eid) or {"id": eid, "status": "approved"}, 200))

    @app.get("/api/v1/events")
    def events(cursor: int = 0, limit: int = 50, project_id: str | None = None, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "audit.read")
        return company.events_page(cursor, limit, project_id)

    @app.get("/api/v1/projects/{project_id}/skills")
    def project_skills(project_id: str, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        row = company.db.execute("SELECT * FROM project_capabilities WHERE project_id=?", (project_id,)).fetchone()
        assignments = [dict(r) for r in company.db.execute(
            "SELECT * FROM learning_assignments WHERE project_id=? ORDER BY created_at", (project_id,))]
        return {"project_id": project_id, "capabilities": dict(row) if row else None,
                "gaps": company.project_skill_gaps(project_id), "learning": assignments}

    @app.post("/api/v1/learning/{assignment_id}/study")
    def study(assignment_id: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "intelligence.ingest")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"id": assignment_id}, lambda: ({"signal_id": company.study_skill(
            ident["principal_id"], assignment_id, payload["source"], payload["title"],
            payload["published_at"], payload["observed_at"], payload.get("summary", ""))}, 200))

    @app.post("/api/v1/learning/{assignment_id}/certify")
    def certify(assignment_id: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "artifact.accept")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"id": assignment_id}, lambda: ({"skill_id": company.certify_skill(ident["principal_id"], assignment_id)}, 200))

    @app.get("/api/v1/headquarters")
    def hq(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.headquarters()

    @app.post("/api/v1/consultant-proposals")
    def consultant_submit(body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "consultant.propose")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: ({"id": desk.submit(ident["principal_id"], payload["proposal"])}, 200))

    @app.post("/api/v1/consultant-proposals/{pid}/decision")
    def consultant_decide(pid: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "consultant.decide")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"id": pid}, lambda: (desk.decide(ident["principal_id"], pid, payload["decision"], payload.get("reason", "decision"), payload.get("expected_source_hash")) or {"id": pid}, 200))

    @app.post("/api/v1/consultant-proposals/{pid}/revise")
    def consultant_revise(pid: str, body: Command, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "consultant.propose")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"id": pid}, lambda: ({"id": desk.revise(ident["principal_id"], pid, payload["proposal"])}, 200))

    @app.get("/api/v1/consultant-proposals")
    def consultant_list(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "consultant.read")
        return {"proposals": desk.list()}

    @app.middleware("http")
    async def reject_spoof(request: Request, call_next):
        return await call_next(request)

    return app


def bootstrap_owner(company: Company, token_path: Path, principal_id="human-ceo"):
    token_path.parent.mkdir(parents=True, exist_ok=True)
    if token_path.is_file():
        return token_path.read_text().strip()
    import secrets
    token = secrets.token_urlsafe(32)
    if not company.identity_for_token(token) and not company.db.execute("SELECT 1 FROM identities WHERE principal_id=?", (principal_id,)).fetchone():
        company.register_identity(principal_id, "owner", token, ["*"])
    token_path.write_text(token)
    token_path.chmod(0o600)
    return token


def resolve_paths(args):
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = Path(data_dir) / "company.db" if args.db == DEFAULT_DB else Path(args.db)
    token_path = Path(data_dir) / "owner.token" if args.token_file == DEFAULT_TOKEN_FILE else Path(args.token_file)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return data_dir, db_path, token_path


def main():
    parser = argparse.ArgumentParser(description="FS-Corporation control service")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                        help="Data directory (default .local; production uses /var/lib/fs-corporation)")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--token-file", default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--allow-remote", action="store_true",
                        help="Allow binding beyond loopback (use with Tailscale or private network)")
    args = parser.parse_args()
    loopback = {"127.0.0.1", "localhost", "::1"}
    if args.host not in loopback and not args.allow_remote:
        raise SystemExit(
            "Refusing to bind a non-loopback address without --allow-remote. "
            "Use Tailscale and bind to your tailnet IP, or keep 127.0.0.1 for local-only access.")
    data_dir, db_path, token_path = resolve_paths(args)
    bind_mode = "loopback" if args.host in loopback else "remote (--allow-remote)"
    companion_dist = data_dir / "companion" / "dist"
    import sys
    print(f"FS-Corporation {__version__}: bind={args.host}:{args.port} mode={bind_mode}", file=sys.stderr)
    print(f"  data-dir={data_dir} db={db_path} token-file={token_path}", file=sys.stderr)
    print(f"  companion-dist={companion_dist} (served by Caddy in production)", file=sys.stderr)
    if args.host not in loopback:
        print("WARNING: control service bound to a non-loopback address; restrict access to your private network.",
              file=sys.stderr)
    company = Company(str(db_path))
    bootstrap_owner(company, token_path)
    import uvicorn
    uvicorn.run(create_app(company), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
