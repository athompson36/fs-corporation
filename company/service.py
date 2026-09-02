"""Loopback control service. Not a trusted remote API."""
from __future__ import annotations
import argparse
import asyncio
import json
import os
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
<meta name="theme-color" content="#070b14"/>
<style>
:root {
  color-scheme: dark;
  --midnight: #070b14;
  --midnight-elev: #0c1220;
  --glass: rgba(16, 24, 40, 0.62);
  --glass-border: rgba(120, 170, 255, 0.22);
  --cosmic: #3b82f6;
  --cosmic-deep: #1d4ed8;
  --ultraviolet: #8b5cf6;
  --aurora: #34d399;
  --soft: #e8eef8;
  --muted: #9aa8c0;
  --warning: #f5b942;
}
* { box-sizing: border-box; }
body { font-family: system-ui, sans-serif; background: radial-gradient(1200px 600px at 10% -10%, #12203a 0%, var(--midnight) 55%); color: var(--soft); margin: 0; }
.shell { display: grid; grid-template-columns: 13rem 1fr; min-height: 100vh; }
.rail { background: var(--midnight-elev); border-right: 1px solid var(--glass-border); padding: 1.1rem 0.9rem; position: sticky; top: 0; height: 100vh; }
.brand { font-weight: 700; letter-spacing: 0.04em; margin: 0 0 1rem; color: var(--soft); }
.rail nav { display: flex; flex-direction: column; gap: 0.25rem; }
.rail a { color: var(--soft); text-decoration: none; padding: 0.45rem 0.65rem; border-radius: 0.65rem; font-size: 0.92rem; }
.rail a:hover, .rail a:focus-visible { background: rgba(59,130,246,0.16); box-shadow: inset 0 0 0 1px var(--cosmic); }
.workspace { padding: 1.25rem 1.5rem 2rem; }
.lede { color: var(--muted); margin: 0 0 1rem; }
.metrics { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 0.75rem; margin-bottom: 0.75rem; }
.metric .value { font-size: 1.8rem; font-weight: 700; letter-spacing: 0.04em; }
.desk-grid { display: grid; grid-template-columns: 1.35fr 1fr; gap: 0.75rem; }
.glass { background: var(--glass); backdrop-filter: blur(16px); border: 1px solid var(--glass-border); border-radius: 1rem; padding: 1rem; margin: 0 0 0.75rem; box-shadow: 0 0 0 1px rgba(255,255,255,0.03), 0 12px 40px rgba(0,0,0,0.28); }
h1, h2, h3 { margin: 0 0 0.5rem; }
h1 { font-size: 1.7rem; }
h2 { font-size: 1.05rem; }
.muted { color: var(--muted); }
.row { display: flex; gap: 0.4rem; flex-wrap: wrap; margin: 0 0 0.6rem; }
.chip { border: 1px solid var(--glass-border); background: rgba(8,12,22,0.5); color: var(--soft); border-radius: 999px; padding: 0.2rem 0.65rem; font-size: 0.8rem; }
.chip.active { border-color: var(--cosmic); background: rgba(59,130,246,0.18); }
.tag { display: inline-block; border-radius: 999px; padding: 0.1rem 0.5rem; font-size: 0.75rem; }
.tag-success { color: var(--aurora); border: 1px solid rgba(52,211,153,0.4); }
.tag-proposal { color: #d8c4ff; border: 1px solid rgba(139,92,246,0.45); }
.tag-warning { color: var(--warning); border: 1px solid rgba(245,185,66,0.4); }
button.room { background: none; border: 0; color: var(--cosmic); cursor: pointer; padding: 0; font: inherit; text-align: left; }
#iso, #floor { width: 100%; max-height: 16rem; }
#iso [data-room-id], #floor [data-room-id] { cursor: pointer; }
.iso-rise { transform-box: fill-box; transform-origin: center bottom; animation: iso-rise 0.7s ease-out; }
@keyframes iso-rise { from { transform: translateY(8px); opacity: 0.4; } to { transform: none; opacity: 1; } }
@media (max-width: 840px) {
  .shell { grid-template-columns: 1fr; }
  .rail { position: static; height: auto; display: block; }
  .rail nav { flex-direction: row; flex-wrap: wrap; }
  .metrics, .desk-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
</head>
<body data-theme="cosmic-glass">
<div class="shell">
<aside class="rail" id="sidebar">
<p class="brand">FS-Corporation</p>
<nav aria-label="Primary">
<a href="#desk">CEO desk</a>
<a href="#hq">Headquarters</a>
<a href="#projects">Projects</a>
<a href="#departments">Departments</a>
<a href="#people">People</a>
<a href="#intelligence">Intelligence</a>
<a href="#decisions">Decisions</a>
<a href="#budget">Budget</a>
<a href="#activity">Activity</a>
<a href="#consultant">Consultant</a>
</nav>
</aside>
<main class="workspace">
<header>
<h1 id="desk">CEO desk</h1>
<p class="lede">A clear view of persisted company state. Occupancy is not running-model count.</p>
</header>
<div class="metrics">
<section class="glass metric" id="metric-projects-card"><h2>Projects</h2><div class="value" id="metric-projects">00</div></section>
<section class="glass metric" id="metric-decisions-card"><h2>Pending decisions</h2><div class="value" id="metric-decisions">00</div></section>
<section class="glass metric" id="metric-departments-card"><h2>Departments</h2><div class="value" id="metric-departments">00</div></section>
</div>
<div class="desk-grid">
<section class="glass" id="hq">
<h2>Headquarters</h2>
<p class="muted">Geometric tiles from expansion events only. Empty HQ draws no invented rooms.</p>
<div class="row" role="group" aria-label="Headquarters view">
<button type="button" class="chip active" data-hq-view="iso">Isometric</button>
<button type="button" class="chip" data-hq-view="plan">Plan</button>
<button type="button" class="chip" data-hq-view="list">List</button>
</div>
<svg id="iso" viewBox="0 0 220 140" role="img" aria-label="isometric projection of provisioned rooms"></svg>
<svg id="floor" viewBox="0 0 200 80" role="img" aria-label="2D floor plan of provisioned rooms" hidden></svg>
<ul id="room-list" hidden></ul>
</section>
<div>
<section class="glass" id="decisions"><h2>Decisions inbox</h2><ul id="proposal-list"></ul></section>
<section class="glass" id="room-detail" hidden>
<h2>Room</h2>
<p id="room-purpose" class="muted"></p>
<ul id="room-facts"></ul>
</section>
</div>
</div>
<section class="glass" id="status"><h2>Status</h2><pre id="status-json">Loading…</pre></section>
<section class="glass" id="consultant"><h2>Consultant inbox</h2><ul id="consultant-list"></ul></section>
<section class="glass" id="projects"><h2>Projects</h2><ul id="project-list"></ul></section>
<section class="glass" id="departments"><h2>Departments</h2><ul id="department-list"></ul></section>
<section class="glass" id="people"><h2>People</h2><ul id="people-list"></ul></section>
<section class="glass" id="intelligence"><h2>Intelligence</h2><p class="muted">Sourced signal events only.</p><ul id="intelligence-list"></ul></section>
<section class="glass" id="budget"><h2>Budget</h2>
<p class="muted">Simulated credits, not billed cost.</p>
<pre id="budget-json">Loading…</pre>
</section>
<section class="glass" id="activity"><h2>Activity</h2><ul id="activity-list"></ul></section>
<section class="glass" id="pairing">
<h2>Phone pairing</h2>
<p class="muted">Issues a one-time QR. The companion redeems it for a scoped device token — never the root owner token. Tailscale join material is returned only on redeem when FS_CORP_TAILSCALE_AUTHKEY is set on the host.</p>
<div class="row" id="pair-levels" role="group" aria-label="Access level"></div>
<p id="pair-level-summary" class="muted"></p>
<p id="pair-remote-status" class="muted"></p>
<div class="row">
<button type="button" class="chip" id="pair-btn">Create pairing QR</button>
</div>
<div id="pair-qr" class="muted">No active pairing ticket.</div>
<p id="pair-url" class="muted"></p>
<h3>Paired devices</h3>
<ul id="pair-devices" class="muted"></ul>
</section>
</main>
</div>
<script>
const headers = {Authorization: 'Bearer ' + (localStorage.getItem('ownerToken')||'')};
function fill(id, items, text) {
  const el = document.getElementById(id);
  el.innerHTML = '';
  items.forEach(item => {
    const li = document.createElement('li');
    li.textContent = text(item);
    el.appendChild(li);
  });
}
function listed(items, fn) {
  const arr = items || [];
  return arr.length ? arr.map(fn).join(', ') : 'none';
}
function pad(n) { return String(n).padStart(2, '0'); }
function setHqView(mode) {
  document.getElementById('iso').hidden = mode !== 'iso';
  document.getElementById('floor').hidden = mode !== 'plan';
  document.getElementById('room-list').hidden = mode !== 'list';
  document.querySelectorAll('[data-hq-view]').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-hq-view') === mode);
  });
}
document.querySelectorAll('[data-hq-view]').forEach(btn => {
  btn.addEventListener('click', () => setHqView(btn.getAttribute('data-hq-view')));
});
let pairAccessLevel = 'admin';
let pairingLevels = [];
function renderPairLevels() {
  const row = document.getElementById('pair-levels');
  const summary = document.getElementById('pair-level-summary');
  row.innerHTML = '';
  pairingLevels.forEach(level => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'chip' + (level.id === pairAccessLevel ? ' active' : '');
    btn.textContent = level.label;
    btn.addEventListener('click', () => {
      pairAccessLevel = level.id;
      renderPairLevels();
    });
    row.appendChild(btn);
  });
  const active = pairingLevels.find(l => l.id === pairAccessLevel);
  summary.textContent = active ? active.summary + ' Scopes: ' + (active.scopes || []).join(', ') : '';
}
async function loadRemoteAccess() {
  const res = await fetch('/api/v1/remote-access', {headers});
  if (!res.ok) return;
  const body = await res.json();
  pairingLevels = body.pairing_levels || [];
  if (pairingLevels.length && !pairingLevels.some(l => l.id === pairAccessLevel)) {
    pairAccessLevel = pairingLevels[pairingLevels.length - 1].id;
  }
  renderPairLevels();
  const status = document.getElementById('pair-remote-status');
  const parts = [];
  if (body.recommended_url) parts.push('URL ' + body.recommended_url);
  if (body.tailnet_ipv4) parts.push('Tailscale ' + body.tailnet_ipv4);
  parts.push(body.auth_key_configured ? 'Tailscale auth key configured' : 'Tailscale auth key not configured');
  status.textContent = parts.join(' · ');
  renderPairedDevices(body.paired_devices || []);
}
function renderPairedDevices(devices) {
  const list = document.getElementById('pair-devices');
  list.innerHTML = '';
  if (!devices.length) {
    const li = document.createElement('li');
    li.textContent = 'No active paired devices.';
    list.appendChild(li);
    return;
  }
  devices.forEach(device => {
    const li = document.createElement('li');
    li.textContent = device.label + ' · ' + device.principal_id + ' · since ' + (device.redeemed_at || '?');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'chip';
    btn.textContent = 'Revoke';
    btn.addEventListener('click', async () => {
      if (!window.confirm('Revoke ' + device.principal_id + '?')) return;
      const res = await fetch('/api/v1/remote-access/revoke/' + encodeURIComponent(device.principal_id), {
        method: 'POST',
        headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'revoke-' + device.principal_id},
        body: JSON.stringify({payload: {}})
      });
      if (!res.ok) {
        const body = await res.json();
        alert(body.detail || 'Revoke failed');
        return;
      }
      loadRemoteAccess();
    });
    li.appendChild(document.createTextNode(' '));
    li.appendChild(btn);
    list.appendChild(li);
  });
}
loadRemoteAccess();
document.getElementById('pair-btn').addEventListener('click', async () => {
  const res = await fetch('/api/v1/remote-access/pairing', {
    method: 'POST',
    headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'pair-' + Date.now()},
    body: JSON.stringify({payload: {access_level: pairAccessLevel}})
  });
  const body = await res.json();
  const box = document.getElementById('pair-qr');
  const url = document.getElementById('pair-url');
  if (!res.ok) {
    box.textContent = body.detail || 'Pairing failed';
    url.textContent = '';
    return;
  }
  const result = body.result || body;
  box.innerHTML = result.qr_svg || '';
  const level = result.label || pairAccessLevel;
  url.textContent = (result.pair_url || '') + ' · ' + level + ' · expires ' + (result.expires_at || '');
});
async function openRoom(roomId) {
  const panel = document.getElementById('room-detail');
  const facts = document.getElementById('room-facts');
  const res = await fetch('/api/v1/headquarters/rooms/' + encodeURIComponent(roomId), {headers});
  const detail = await res.json();
  if (!res.ok) {
    panel.hidden = false;
    document.getElementById('room-purpose').textContent = detail.detail || 'Room not found';
    facts.innerHTML = '';
    return;
  }
  panel.hidden = false;
  document.getElementById('room-purpose').textContent = detail.purpose;
  const lines = [
    detail.room.id + ' — ' + detail.room.status + ' — ' + detail.room.source_project,
    'Tasks: ' + listed(detail.tasks, t => t.id),
    'Staff: ' + listed(detail.staff, s => s.display_name + ' (' + s.position_id + ')'),
    'Deliverables: ' + listed(detail.deliverables, d => d.hash.slice(0,12)),
    'Decisions: ' + listed(detail.decisions, d => d.kind),
    'Simulated spend: ' + detail.costs.simulated_spend_cents + '¢ reserved ' + detail.costs.reserved_cents + '¢',
    detail.occupancy_note
  ];
  facts.innerHTML = '';
  lines.forEach(line => { const li = document.createElement('li'); li.textContent = line; facts.appendChild(li); });
  location.hash = 'room-detail';
}
async function load() {
  const status = await fetch('/api/v1/company', {headers});
  document.getElementById('status-json').textContent = await status.text();
  const hq = await fetch('/api/v1/headquarters', {headers});
  const data = await hq.json();
  const list = document.getElementById('room-list');
  list.innerHTML = '';
  (data.rooms||[]).forEach(room => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.className = 'room';
    btn.type = 'button';
    btn.textContent = room.id + ' — ' + room.status + ' — ' + room.source_project;
    btn.addEventListener('click', () => openRoom(room.id));
    li.appendChild(btn);
    list.appendChild(li);
  });
  const cons = await fetch('/api/v1/consultant-proposals', {headers});
  const cj = await cons.json();
  fill('consultant-list', cj.proposals||[], p => ((p.body && p.body.title) ? p.body.title : p.id) + ' — ' + p.status);
  const inbox = await fetch('/api/v1/decisions/inbox', {headers});
  const ij = await inbox.json();
  fill('proposal-list', ij.items||[], item => item.kind + ' — ' + item.title);
  const ev = await fetch('/api/v1/events?limit=20', {headers});
  const ej = await ev.json();
  fill('activity-list', ej.items||[], item => item.kind + ' @ ' + item.at);
  const projects = await fetch('/api/v1/projects', {headers});
  const pj = await projects.json();
  fill('project-list', pj.projects||[], p => p.id + ' — ' + (p.brief || p.status || ''));
  const depts = await fetch('/api/v1/departments', {headers});
  const dj = await depts.json();
  fill('department-list', dj.departments||[], d => d.id + ' — ' + d.name + ' — ' + d.head_title);
  const people = await fetch('/api/v1/hr/development', {headers});
  const peoplej = await people.json();
  fill('people-list', peoplej.employees || peoplej.assignments || [], p => (p.display_name || p.employee_id || p.id) + ' — ' + (p.position_id || p.status || ''));
  fill('intelligence-list', (ej.items||[]).filter(item => String(item.kind).startsWith('signal')), item => item.kind + ' @ ' + item.at);
  const dash = await fetch('/api/v1/dashboard', {headers});
  const dashj = await dash.json();
  const company = dashj.company || {};
  document.getElementById('metric-projects').textContent = pad((pj.projects||[]).length);
  document.getElementById('metric-decisions').textContent = pad((ij.items||[]).length);
  document.getElementById('metric-departments').textContent = pad((dj.departments||[]).length);
  document.getElementById('budget-json').textContent = JSON.stringify({
    simulated_spend_cents: company.simulated_spend_cents,
    reserved_cents: company.reserved_cents,
    note: 'Simulated credits, not billed cost'
  });
  const svg = document.getElementById('floor');
  svg.innerHTML = '';
  const iso = document.getElementById('iso');
  iso.innerHTML = '';
  function ns(name) { return document.createElementNS('http://www.w3.org/2000/svg', name); }
  (data.rooms||[]).forEach((room, i) => {
    const x = 10 + (i % 4) * 48;
    const y = 10 + Math.floor(i / 4) * 36;
    const r = ns('rect');
    r.setAttribute('x', x); r.setAttribute('y', y);
    r.setAttribute('width', 40); r.setAttribute('height', 28);
    r.setAttribute('fill', room.status === 'built' ? '#1d4ed8' : '#1a2233');
    r.setAttribute('stroke', room.status === 'built' ? '#3b82f6' : '#8b5cf6');
    r.setAttribute('data-room-id', room.id);
    r.addEventListener('click', () => openRoom(room.id));
    svg.appendChild(r);
    const t = ns('text');
    t.setAttribute('x', x+4); t.setAttribute('y', y+16); t.setAttribute('fill', '#eee');
    t.setAttribute('font-size', '6');
    t.textContent = room.status;
    svg.appendChild(t);
    const col = i % 4, row = Math.floor(i / 4);
    const ix = 100 + (col - row) * 28, iy = 28 + (col + row) * 16;
    const built = room.status === 'built';
    const h = built ? 16 : 6;
    const g = ns('g');
    g.setAttribute('data-room-id', room.id);
    if (built) g.setAttribute('class', 'iso-rise');
    g.addEventListener('click', () => openRoom(room.id));
    const top = ns('polygon');
    top.setAttribute('points', [ix,iy-h, ix+24,iy-h+12, ix,iy-h+24, ix-24,iy-h+12].join(' '));
    top.setAttribute('fill', built ? '#3b82f6' : '#2a2040');
    top.setAttribute('stroke', built ? '#93c5fd' : '#8b5cf6');
    const left = ns('polygon');
    left.setAttribute('points', [ix-24,iy-h+12, ix,iy-h+24, ix,iy+24, ix-24,iy+12].join(' '));
    left.setAttribute('fill', built ? '#1e3a8a' : '#1a1630');
    const right = ns('polygon');
    right.setAttribute('points', [ix+24,iy-h+12, ix,iy-h+24, ix,iy+24, ix+24,iy+12].join(' '));
    right.setAttribute('fill', built ? '#1d4ed8' : '#161225');
    const label = ns('text');
    label.setAttribute('x', ix-10); label.setAttribute('y', iy-h+16);
    label.setAttribute('fill', '#eee'); label.setAttribute('font-size', '6');
    label.textContent = room.status;
    g.appendChild(left); g.appendChild(right); g.appendChild(top); g.appendChild(label);
    iso.appendChild(g);
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
    if os.environ.get("FS_CORP_ALLOW_CORS") == "1":
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://127.0.0.1:4173",
                "http://localhost:4173",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
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

    @app.get("/api/v1/push/subscriptions")
    def push_list(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return {"subscriptions": company.list_push_subscriptions(ident["principal_id"])}

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

    @app.post("/api/v1/push/notify")
    def push_notify(body: Command, authorization: str | None = Header(default=None),
                    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        kind = payload.get("kind") or "owner_inbox"
        subject = payload.get("subject") or "FS-Corporation test notification"
        extra = {k: v for k, v in payload.items() if k not in {"kind", "subject"}}
        return run(ident, idempotency_key, payload, lambda: (
            company.notify_push(kind, subject, extra), 200))

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
        scratch = payload.get("scratch_root") or os.environ.get("FS_CORP_WORKER_SCRATCH") or tempfile.mkdtemp(prefix="company-worker-")
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

    @app.get("/api/v1/slos")
    def list_slos(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.list_slos()

    @app.post("/api/v1/slos/{slo_id}/observations")
    def record_slo(slo_id: str, body: Command, authorization: str | None = Header(default=None),
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"slo_id": slo_id}, lambda: (
            company.record_slo_observation(
                ident["principal_id"], slo_id, payload["value"], payload["source"],
                payload["window_start"], payload["window_end"]), 200))

    @app.post("/api/v1/projects/{project_id}/github-enrollment")
    def github_enroll(project_id: str, body: Command, authorization: str | None = Header(default=None),
                      idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "project.enroll")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"project_id": project_id}, lambda: (
            company.enroll_github(
                ident["principal_id"], project_id,
                str(payload["upstream_repo_id"]), str(payload["fork_repo_id"]),
                payload.get("protected_branches") or ["main"],
                payload["branch_prefix"], payload.get("permitted_actions") or ["open_pr"]),
            200))

    @app.get("/api/v1/github/status")
    def github_status(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        from company.github_app import status_summary
        return status_summary()

    @app.get("/api/v1/model/status")
    def model_status(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        from company.model_provider import status_summary
        return status_summary()

    @app.get("/api/v1/feeds")
    def list_feeds(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return {"feeds": company.list_feed_sources()}

    @app.post("/api/v1/feeds")
    def approve_feed(body: Command, authorization: str | None = Header(default=None),
                     idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "project.enroll")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (
            company.approve_feed_source(ident["principal_id"], payload["id"], payload["url"]), 200))

    @app.post("/api/v1/feeds/{source_id}/poll")
    def poll_feed(source_id: str, body: Command, authorization: str | None = Header(default=None),
                  idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"source_id": source_id}, lambda: (
            company.poll_market_feed(source_id, actor=ident["principal_id"]), 200))

    @app.get("/api/v1/push/status")
    def push_status(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        from company.push_vapid import status_summary
        return status_summary()

    @app.get("/api/v1/workers/status")
    def workers_status(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        from company.worker_status import status_summary
        return status_summary()

    @app.get("/api/v1/remote-access")
    def remote_access(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        public = os.environ.get("FS_CORP_PUBLIC_URL")
        status = company.remote_access_status(public)
        try:
            company._ceo(ident["principal_id"])
            status["paired_devices"] = company.list_paired_devices(ident["principal_id"])
        except PermissionError:
            status["paired_devices"] = []
        return status

    @app.post("/api/v1/remote-access/revoke/{principal_id}")
    def remote_revoke(principal_id: str, body: Command, authorization: str | None = Header(default=None),
                      idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"principal_id": principal_id}, lambda: (
            company.revoke_paired_device(ident["principal_id"], principal_id), 200))

    @app.post("/api/v1/remote-access/pairing")
    def remote_pairing(request: Request, body: Command, authorization: str | None = Header(default=None),
                       idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        public = (os.environ.get("FS_CORP_PUBLIC_URL") or str(request.base_url)).rstrip("/")
        access_level = (payload.get("access_level") or "admin").strip()
        return run(ident, idempotency_key, payload, lambda: (
            company.create_pairing_ticket(ident["principal_id"], public, access_level=access_level), 200))

    @app.post("/api/v1/remote-access/redeem")
    def remote_redeem(body: Command):
        ticket = (body.payload or {}).get("ticket")
        try:
            return company.redeem_pairing_ticket(ticket)
        except LookupError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/headquarters")
    def hq(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.headquarters()

    @app.get("/api/v1/headquarters/rooms/{room_id}")
    def hq_room(room_id: str, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        try:
            return company.room_detail(room_id)
        except LookupError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

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
        # A provisioning step may have written the token file before the service
        # ever ran, so the file existing does not imply a registered identity.
        token = token_path.read_text().strip()
        if token and not company.identity_for_token(token):
            if company.db.execute("SELECT 1 FROM identities WHERE principal_id=?",
                                  (principal_id,)).fetchone():
                raise RuntimeError(
                    f"Owner identity {principal_id!r} is registered with a different token than "
                    f"{token_path}. Refusing to start with an owner token nobody can use. "
                    "Restore the matching token file or re-provision the database.")
            company.register_identity(principal_id, "owner", token, ["*"])
        return token
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
