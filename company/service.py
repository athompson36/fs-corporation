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
from company.rate_limit import (
    EXEMPT_PATHS,
    UNAUTH_LIMITED_PATHS,
    RateLimitPolicy,
    RateLimiter,
    coerce_policy,
)

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
input, textarea { width: 100%; color: var(--soft); background: rgba(8,12,22,0.6); border: 1px solid var(--glass-border); border-radius: 0.5rem; padding: 0.45rem; margin: 0.2rem 0 0.6rem; }
form.compact { border-top: 1px solid var(--glass-border); margin-top: 0.6rem; padding-top: 0.6rem; }
#iso, #floor { width: 100%; max-height: 16rem; }
#iso [data-room-id], #floor [data-room-id], #floor [data-worker-id] { cursor: pointer; }
.iso-rise { transform-box: fill-box; transform-origin: center bottom; animation: iso-rise 0.7s ease-out; }
.activity-badge { fill: var(--warning); stroke: var(--soft); stroke-width: 0.7; pointer-events: none; }
.activity-pulse { animation: activity-pulse 1.8s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
@keyframes iso-rise { from { transform: translateY(8px); opacity: 0.4; } to { transform: none; opacity: 1; } }
@keyframes activity-pulse { 50% { transform: scale(1.35); opacity: 0.7; } }
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
<a href="#scorecard">Scorecard</a>
<a href="#hq">Headquarters</a>
<a href="#projects">Projects</a>
<a href="#departments">Departments</a>
<a href="#cross-department">Cross-department</a>
<a href="#corporate-upgrades">Corporate upgrades</a>
<a href="#people">People</a>
<a href="#intelligence">Intelligence</a>
<a href="#decisions">Decisions</a>
<a href="#budget">Budget</a>
<a href="#diagnostics">Diagnostics</a>
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
<section class="glass" id="scorecard">
<h2>CEO scorecard</h2>
<p class="muted">Measured from persisted operations — not simulated.</p>
<pre id="scorecard-metrics">Loading…</pre>
<h3>Objectives</h3>
<ul id="objective-list"></ul>
<form id="objective-create-form" class="compact">
<h3>Create objective</h3>
<label for="objective-title">Title</label><input id="objective-title" required/>
<label for="objective-due-at">Due at</label><input id="objective-due-at" type="datetime-local" required/>
<label for="objective-division">Division id (optional)</label><input id="objective-division"/>
<label for="objective-target">Target JSON (optional)</label>
<textarea id="objective-target" placeholder='{"accepted_artifacts": 5}'></textarea>
<button type="submit" class="chip">Create objective</button><span class="muted"></span>
</form>
</section>
<div class="desk-grid">
<section class="glass" id="hq">
<h2>Headquarters</h2>
<p class="muted">Persisted department rooms when planned; expansion events remain the fallback.</p>
<div id="unmet-requirements" class="row" aria-label="Unmet room requirements"></div>
<div class="row">
<button type="button" class="chip" id="default-floorplan-btn">Create default floorplan</button>
<span id="default-floorplan-status" class="muted"></span>
</div>
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
<section class="glass" id="worker-card" hidden>
<h2 id="worker-name">Worker</h2>
<p id="worker-headline" class="muted"></p>
<ul id="worker-facts"></ul>
</section>
</div>
</div>
<section class="glass" id="status"><h2>Status</h2><pre id="status-json">Loading…</pre></section>
<section class="glass" id="consultant"><h2>Consultant inbox</h2><ul id="consultant-list"></ul></section>
<section class="glass" id="projects"><h2>Projects</h2><ul id="project-list"></ul>
<form id="dispatch-form" class="compact">
<h3>Dispatch brief to heads</h3>
<label for="dispatch-project">Project id</label><input id="dispatch-project" required/>
<label for="dispatch-brief-template">Brief template</label>
<select id="dispatch-brief-template"><option value="">Custom / free text</option></select>
<label for="dispatch-brief">Brief</label><textarea id="dispatch-brief" required></textarea>
<label for="dispatch-criteria-template">Acceptance criteria template</label>
<select id="dispatch-criteria-template"><option value="">Custom / free text</option></select>
<label for="dispatch-criteria">Acceptance criteria</label><textarea id="dispatch-criteria" required></textarea>
<div id="dispatch-dept-list" class="dispatch-dept-list"></div>
<label for="dispatch-budgets">Department budgets (advanced; synced from list)</label>
<textarea id="dispatch-budgets" placeholder="engineering=500&#10;product=300" required></textarea>
<div class="row" role="group" aria-label="Dispatch actions">
<button type="button" class="chip" id="dispatch-recommend-btn">Recommend for this project</button>
<button type="submit" class="chip" id="dispatch-submit-btn">Dispatch</button>
</div>
<details id="dispatch-valid-values"><summary>Valid values</summary>
<pre id="dispatch-valid-values-body" class="muted">Load a project id to see templates, presets, and department status.</pre>
</details>
<p id="dispatch-status" class="muted"></p>
</form>
<h3>Local candidates</h3>
<p class="muted">Folders under local repos/ on the host. Enroll creates a company project (id = folder name).</p>
<ul id="local-repo-list"></ul>
</section>
<section class="glass" id="departments"><h2>Organization</h2>
<p class="muted">Catalog, persisted seat status, and roster. Vacant and dormant seats are not active workers.</p>
<ul id="org-list"></ul>
<form id="create-department-form" class="compact">
<h3>Create department</h3>
<label for="desk-dept-id">Id</label><input id="desk-dept-id" required/>
<label for="desk-dept-name">Name</label><input id="desk-dept-name" required/>
<label for="desk-dept-head">Head title</label><input id="desk-dept-head" required/>
<label for="desk-dept-mission">Mission</label><input id="desk-dept-mission" required/>
<label for="desk-dept-room">Room type</label><input id="desk-dept-room" value="boardroom" required/>
<label for="desk-dept-active"><input type="checkbox" id="desk-dept-active"/> Initially active</label>
<button type="submit" class="chip">Create department</button><span class="muted"></span>
</form>
<form id="appoint-head-form" class="compact">
<h3>Appoint department head</h3>
<label for="desk-appoint-department">Department id</label><input id="desk-appoint-department" required/>
<label for="desk-appoint-principal">Principal id</label><input id="desk-appoint-principal" required/>
<button type="submit" class="chip">Appoint head</button><span class="muted"></span>
</form>
<form id="vacate-head-form" class="compact">
<h3>Vacate department head</h3>
<label for="desk-vacate-department">Department id</label><input id="desk-vacate-department" required/>
<button type="submit" class="chip">Vacate head</button><span class="muted"></span>
</form>
<form id="assign-position-form" class="compact">
<h3>Assign position</h3>
<label for="desk-position-id">Position id</label><input id="desk-position-id" placeholder="engineering:Developer" required/>
<label for="desk-position-principal">Principal id</label><input id="desk-position-principal" required/>
<label for="desk-position-reports-to">Reports-to seat id (optional)</label>
<input id="desk-position-reports-to" placeholder="seat:engineering"/>
<button type="submit" class="chip">Assign position</button><span class="muted"></span>
</form>
<form id="release-assignment-form" class="compact">
<h3>Release assignment</h3>
<label for="desk-release-assignment">Assignment id</label><input id="desk-release-assignment" required/>
<button type="submit" class="chip">Release assignment</button><span class="muted"></span>
</form>
<form id="create-position-form" class="compact">
<h3>Create position</h3>
<label for="desk-create-pos-dept">Department id</label><input id="desk-create-pos-dept" required/>
<label for="desk-create-pos-title">Title</label><input id="desk-create-pos-title" required/>
<button type="submit" class="chip">Create position</button><span class="muted"></span>
</form>
<form id="reorder-departments-form" class="compact">
<h3>Reorder departments</h3>
<label for="desk-reorder-items">Items JSON</label>
<textarea id="desk-reorder-items" placeholder='[{"id":"engineering","display_order":10},{"id":"art","display_order":5}]' required></textarea>
<button type="submit" class="chip">Reorder</button><span class="muted"></span>
</form>
</section>
<section class="glass" id="cross-department">
<h2>Cross-department requests</h2>
<p class="muted">Governed work between departments. List is scoped to the delivering head or CEO.</p>
<ul id="cross-dept-list"></ul>
<form id="cross-dept-create-form" class="compact">
<h3>Create request</h3>
<label for="xd-project">Project id</label><input id="xd-project" required/>
<label for="xd-requesting">Requesting department</label><input id="xd-requesting" required/>
<label for="xd-delivering">Delivering department</label><input id="xd-delivering" required/>
<label for="xd-subject">Subject</label><input id="xd-subject" required/>
<label for="xd-brief">Brief</label><textarea id="xd-brief" required></textarea>
<label for="xd-accept">Acceptance criteria</label><textarea id="xd-accept" required></textarea>
<label for="xd-budget-owner">Budget owner</label><input id="xd-budget-owner" required/>
<label for="xd-budget">Budget cents</label><input id="xd-budget" type="number" min="0" required/>
<label for="xd-due">Due at</label><input id="xd-due" type="datetime-local" required/>
<label for="xd-escalation">Escalation path</label><input id="xd-escalation" value="owner" required/>
<button type="submit" class="chip">Create request</button><span class="muted"></span>
</form>
</section>
<section class="glass" id="corporate-upgrades">
<h2>Corporate upgrades</h2>
<p class="muted">Industry packs are templates. Divisions remain proposals until the CEO activates them.</p>
<h3>Industry packs</h3><ul id="industry-pack-list"></ul>
<h3>Divisions</h3><ul id="division-list"></ul>
<form id="division-proposal-form" class="compact">
<h3>Propose division</h3>
<label for="division-pack-id">Industry pack id</label><input id="division-pack-id" required/>
<label for="division-name">Division name</label><input id="division-name" required/>
<label for="division-mode">Mode</label>
<select id="division-mode"><option value="minimal">Minimal</option><option value="full">Full</option></select>
<button type="submit" class="chip">Propose</button><span class="muted"></span>
</form>
</section>
<section class="glass" id="head-inbox"><h2>Head inbox</h2>
<p class="muted">Open dispatches returned for this authenticated principal.</p>
<ul id="head-inbox-list"></ul>
</section>
<section class="glass" id="people">
<h2>People</h2><ul id="people-list"></ul>
<h3>Pending promotions</h3><ul id="promotion-list"></ul>
<div class="row">
<button type="button" class="chip" id="staffing-scan-btn">Scan staffing gaps</button>
<span id="staffing-scan-status" class="muted"></span>
</div>
<h3>Pending staffing proposals</h3><ul id="staffing-proposal-list"></ul>
</section>
<section class="glass" id="intelligence"><h2>Intelligence</h2><p class="muted">Impact briefs from sourced signals (no auto-publish).</p><ul id="intelligence-list"></ul></section>
<section class="glass" id="budget"><h2>Budget</h2>
<p class="muted">Simulated credits, billed cost, and revenue are separate totals.</p>
<pre id="budget-json">Loading…</pre>
</section>
<section class="glass" id="diagnostics"><h2>Diagnostics</h2>
<p class="muted">Live probes only. Missing endpoints show unavailable — nothing is invented.</p>
<button type="button" class="chip" id="diag-refresh">Refresh diagnostics</button>
<div id="diag-blocks"></div>
</section>
<section class="glass" id="activity"><h2>Activity</h2><ul id="activity-list"></ul></section>
<section class="glass" id="pairing">
<h2>Phone pairing</h2>
<p class="muted">Issues a one-time QR. The companion redeems it for a scoped device token — never the root owner token. Tailscale join material is returned only on redeem when FS_CORP_TAILSCALE_AUTHKEY is set on the host.</p>
<div class="row" id="owner-token-row">
<label for="owner-token-input" class="muted">Owner token (stored only in this browser)</label>
<input id="owner-token-input" type="password" autocomplete="off" placeholder="Paste owner token, then Save" style="flex:1;min-width:12rem"/>
<button type="button" class="chip" id="owner-token-save">Save</button>
</div>
<p id="owner-token-status" class="muted"></p>
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
let headers = {Authorization: 'Bearer ' + (localStorage.getItem('ownerToken')||'')};
function refreshOwnerTokenStatus() {
  const status = document.getElementById('owner-token-status');
  const has = !!(localStorage.getItem('ownerToken')||'').trim();
  status.textContent = has ? 'Owner token present in this browser.' : 'No owner token yet — paste from the secure copy, then Save.';
  document.getElementById('owner-token-input').value = '';
}
document.getElementById('owner-token-save').addEventListener('click', () => {
  const value = document.getElementById('owner-token-input').value.trim();
  if (!value) { alert('Paste the owner token first'); return; }
  localStorage.setItem('ownerToken', value);
  headers = {Authorization: 'Bearer ' + value};
  refreshOwnerTokenStatus();
  loadRemoteAccess();
  load();
});
refreshOwnerTokenStatus();
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
let headquartersRooms = [];
function renderActivityBadges(items) {
  document.querySelectorAll('.activity-badge').forEach(node => node.remove());
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const byRoom = new Map();
  (items || []).forEach(item => {
    const fallback = headquartersRooms.find(
      room => room.department_id && room.department_id === item.department_id);
    const roomId = item.room_id || (fallback && fallback.id);
    if (!roomId) return;
    if (!byRoom.has(roomId)) byRoom.set(roomId, []);
    byRoom.get(roomId).push(item);
  });
  byRoom.forEach((sessions, roomId) => {
    const target = Array.from(document.querySelectorAll('#floor [data-room-id]')).find(
      node => node.getAttribute('data-room-id') === roomId);
    if (!target || typeof target.getBBox !== 'function') return;
    const box = target.getBBox();
    const badge = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    badge.setAttribute('cx', box.x + box.width - 4);
    badge.setAttribute('cy', box.y + 4);
    badge.setAttribute('r', Math.min(3.5, 2 + sessions.length * 0.4));
    badge.setAttribute('class', 'activity-badge' + (reduced ? '' : ' activity-pulse'));
    badge.setAttribute(
      'aria-label', sessions.length + ' active session' + (sessions.length === 1 ? '' : 's'));
    document.getElementById('floor').appendChild(badge);
  });
}
async function loadActivity() {
  const response = await fetch('/api/v1/activity', {headers});
  if (!response.ok) return;
  const body = await response.json();
  const items = body.items || [];
  fill(
    'activity-list', items,
    item => item.kind + ' — ' + (item.department_id || 'unassigned') + ' @ ' + item.started_at);
  renderActivityBadges(items);
}
function parseDepartmentBudgets(raw) {
  const departmentBudgets = {};
  raw.split(/\\n/).forEach(line => {
    const parts = line.split('=');
    const id = (parts[0] || '').trim();
    const amount = Number((parts[1] || '').trim());
    if (id && Number.isInteger(amount) && amount >= 0) departmentBudgets[id] = amount;
  });
  return departmentBudgets;
}
let dispatchOptionsCache = null;
function fillTemplateSelect(selectId, templates) {
  const select = document.getElementById(selectId);
  const current = select.value;
  select.innerHTML = '<option value="">Custom / free text</option>';
  (templates || []).forEach(template => {
    const option = document.createElement('option');
    option.value = template.id;
    option.textContent = template.label;
    option.dataset.body = template.body;
    select.appendChild(option);
  });
  if ([...select.options].some(option => option.value === current)) select.value = current;
}
function syncBudgetsTextarea() {
  const lines = [];
  document.querySelectorAll('#dispatch-dept-list .dispatch-dept-row').forEach(row => {
    const check = row.querySelector('input[type="checkbox"]');
    const budget = row.querySelector('input[data-budget]');
    if (check && check.checked && budget) {
      const amount = Number(budget.value);
      if (Number.isInteger(amount) && amount >= 0) lines.push(check.value + '=' + amount);
    }
  });
  document.getElementById('dispatch-budgets').value = lines.join('\\n');
  updateDispatchSubmitGate();
}
function updateDispatchSubmitGate() {
  const status = document.getElementById('dispatch-status');
  const submit = document.getElementById('dispatch-submit-btn');
  let blocked = false;
  document.querySelectorAll('#dispatch-dept-list .dispatch-dept-row').forEach(row => {
    const check = row.querySelector('input[type="checkbox"]');
    if (check && check.checked && check.dataset.dispatchable === 'false') blocked = true;
  });
  submit.disabled = blocked;
  if (blocked) status.textContent = 'Activate dormant departments before dispatch.';
}
function renderDispatchDepartments(options) {
  const host = document.getElementById('dispatch-dept-list');
  host.innerHTML = '';
  const presets = ((options.fields || {}).department_budgets || {}).presets_cents || [];
  const maxCents = ((options.fields || {}).department_budgets || {}).max_cents || 0;
  (options.departments || []).forEach(dept => {
    const row = document.createElement('div');
    row.className = 'dispatch-dept-row';
    const check = document.createElement('input');
    check.type = 'checkbox';
    check.value = dept.id;
    check.id = 'dispatch-dept-' + dept.id;
    check.dataset.dispatchable = dept.dispatchable ? 'true' : 'false';
    check.addEventListener('change', syncBudgetsTextarea);
    const label = document.createElement('label');
    label.htmlFor = check.id;
    label.textContent = dept.name + ' (' + dept.status + (dept.dispatchable ? '' : ' — Activate first') + ')';
    const budget = document.createElement('input');
    budget.type = 'number';
    budget.min = '0';
    budget.max = String(maxCents);
    budget.value = '0';
    budget.dataset.budget = dept.id;
    budget.setAttribute('aria-label', dept.name + ' budget cents');
    budget.addEventListener('input', syncBudgetsTextarea);
    const chips = document.createElement('span');
    chips.className = 'row';
    presets.filter(preset => preset <= maxCents).forEach(preset => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.textContent = String(preset);
      chip.addEventListener('click', () => {
        budget.value = String(preset);
        check.checked = true;
        syncBudgetsTextarea();
      });
      chips.appendChild(chip);
    });
    row.appendChild(check);
    row.appendChild(label);
    row.appendChild(budget);
    row.appendChild(chips);
    host.appendChild(row);
  });
  syncBudgetsTextarea();
}
function renderValidValues(options) {
  const body = document.getElementById('dispatch-valid-values-body');
  const budgets = (options.fields || {}).department_budgets || {};
  const lines = [
    'max_cents=' + budgets.max_cents,
    'presets_cents=' + JSON.stringify(budgets.presets_cents || []),
    'departments=' + (options.departments || []).map(
      dept => dept.id + ':' + dept.status + (dept.dispatchable ? ':ok' : ':dormant')).join(', '),
  ];
  body.textContent = lines.join('\\n');
}
async function loadDispatchOptions() {
  const projectId = document.getElementById('dispatch-project').value.trim();
  const status = document.getElementById('dispatch-status');
  if (!projectId) return;
  const res = await fetch('/api/v1/projects/' + encodeURIComponent(projectId) + '/dispatch-options', {headers});
  if (!res.ok) {
    status.textContent = await res.text();
    return;
  }
  dispatchOptionsCache = await res.json();
  fillTemplateSelect('dispatch-brief-template', dispatchOptionsCache.fields.brief.templates);
  fillTemplateSelect('dispatch-criteria-template', dispatchOptionsCache.fields.acceptance_criteria.templates);
  if (!document.getElementById('dispatch-brief').value) {
    document.getElementById('dispatch-brief').value = dispatchOptionsCache.brief_default || '';
  }
  renderDispatchDepartments(dispatchOptionsCache);
  renderValidValues(dispatchOptionsCache);
  status.textContent = 'Options loaded for ' + projectId + '.';
}
document.getElementById('dispatch-project').addEventListener('change', loadDispatchOptions);
document.getElementById('dispatch-project').addEventListener('blur', loadDispatchOptions);
document.getElementById('dispatch-brief-template').addEventListener('change', event => {
  const option = event.target.selectedOptions[0];
  if (option && option.dataset.body) document.getElementById('dispatch-brief').value = option.dataset.body;
});
document.getElementById('dispatch-criteria-template').addEventListener('change', event => {
  const option = event.target.selectedOptions[0];
  if (option && option.dataset.body) document.getElementById('dispatch-criteria').value = option.dataset.body;
});
document.getElementById('dispatch-recommend-btn').addEventListener('click', async () => {
  const projectId = document.getElementById('dispatch-project').value.trim();
  const status = document.getElementById('dispatch-status');
  if (!projectId) {
    status.textContent = 'Enter a project id first.';
    return;
  }
  if (!dispatchOptionsCache || dispatchOptionsCache.project_id !== projectId) {
    await loadDispatchOptions();
  }
  const res = await fetch('/api/v1/projects/' + encodeURIComponent(projectId) + '/dispatch-recommend', {
    method: 'POST',
    headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'desk-rec-' + Date.now()},
    body: JSON.stringify({payload: {use_live: true}})
  });
  if (!res.ok) {
    status.textContent = await res.text();
    return;
  }
  const wrapped = await res.json();
  const body = wrapped.result || wrapped;
  document.getElementById('dispatch-brief').value = body.brief || '';
  document.getElementById('dispatch-criteria').value = body.acceptance_criteria || '';
  const recommended = new Map((body.departments || []).map(item => [item.id, item]));
  document.querySelectorAll('#dispatch-dept-list .dispatch-dept-row').forEach(row => {
    const check = row.querySelector('input[type="checkbox"]');
    const budget = row.querySelector('input[data-budget]');
    const item = recommended.get(check.value);
    if (item) {
      check.checked = !!item.recommended;
      budget.value = String(item.budget_cents || 0);
    } else {
      check.checked = false;
    }
  });
  syncBudgetsTextarea();
  const notes = (body.notes || []).join(', ');
  status.textContent = 'Recommendation source=' + body.source + (notes ? (' notes=' + notes) : '');
});
document.getElementById('dispatch-form').addEventListener('submit', async event => {
  event.preventDefault();
  syncBudgetsTextarea();
  const departmentBudgets = parseDepartmentBudgets(document.getElementById('dispatch-budgets').value);
  const status = document.getElementById('dispatch-status');
  if (!Object.keys(departmentBudgets).length) {
    status.textContent = 'Select at least one department with a budget.';
    return;
  }
  if (document.getElementById('dispatch-submit-btn').disabled) {
    status.textContent = 'Activate dormant departments before dispatch.';
    return;
  }
  const projectId = document.getElementById('dispatch-project').value.trim();
  const res = await fetch('/api/v1/projects/' + encodeURIComponent(projectId) + '/dispatch-brief', {
    method: 'POST',
    headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'desk-dispatch-' + Date.now()},
    body: JSON.stringify({payload: {
      brief: document.getElementById('dispatch-brief').value.trim(),
      acceptance_criteria: document.getElementById('dispatch-criteria').value.trim(),
      department_budgets: departmentBudgets
    }})
  });
  status.textContent = res.ok ? 'Dispatch created.' : await res.text();
  if (res.ok) { event.target.reset(); dispatchOptionsCache = null; document.getElementById('dispatch-dept-list').innerHTML = ''; load(); }
});
async function submitOrgCommand(form, path, payload, success) {
  const status = form.querySelector('span');
  const res = await fetch(path, {
    method: 'POST',
    headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'desk-org-' + Date.now()},
    body: JSON.stringify({payload})
  });
  status.textContent = res.ok ? ' ' + success : ' ' + await res.text();
  if (res.ok) { form.reset(); load(); }
}
document.getElementById('create-department-form').addEventListener('submit', async event => {
  event.preventDefault();
  await submitOrgCommand(event.target, '/api/v1/org/departments', {
    id: document.getElementById('desk-dept-id').value.trim(),
    name: document.getElementById('desk-dept-name').value.trim(),
    head_title: document.getElementById('desk-dept-head').value.trim(),
    mission: document.getElementById('desk-dept-mission').value.trim(),
    measures: [],
    room_type: document.getElementById('desk-dept-room').value.trim(),
    initially_active: document.getElementById('desk-dept-active').checked,
    default_model_profile: 'mock-text',
  }, 'Department created.');
  event.target.reset();
  load();
});
document.getElementById('appoint-head-form').addEventListener('submit', async event => {
  event.preventDefault();
  await submitOrgCommand(event.target, '/api/v1/org/heads', {
    department_id: document.getElementById('desk-appoint-department').value.trim(),
    principal_id: document.getElementById('desk-appoint-principal').value.trim()
  }, 'Head appointed.');
});
document.getElementById('vacate-head-form').addEventListener('submit', async event => {
  event.preventDefault();
  await submitOrgCommand(event.target, '/api/v1/org/heads', {
    department_id: document.getElementById('desk-vacate-department').value.trim(),
    vacate: true
  }, 'Head vacated.');
});
document.getElementById('assign-position-form').addEventListener('submit', async event => {
  event.preventDefault();
  const reportsTo = document.getElementById('desk-position-reports-to').value.trim();
  const payload = {
    position_id: document.getElementById('desk-position-id').value.trim(),
    principal_id: document.getElementById('desk-position-principal').value.trim()
  };
  if (reportsTo) payload.reports_to_seat_id = reportsTo;
  await submitOrgCommand(event.target, '/api/v1/org/assignments', payload, 'Position assigned.');
});
document.getElementById('release-assignment-form').addEventListener('submit', async event => {
  event.preventDefault();
  await submitOrgCommand(event.target, '/api/v1/org/assignments', {
    assignment_id: document.getElementById('desk-release-assignment').value.trim(),
    release: true
  }, 'Assignment released.');
});
document.getElementById('create-position-form').addEventListener('submit', async event => {
  event.preventDefault();
  await submitOrgCommand(event.target, '/api/v1/org/positions', {
    department_id: document.getElementById('desk-create-pos-dept').value.trim(),
    title: document.getElementById('desk-create-pos-title').value.trim()
  }, 'Position created.');
});
document.getElementById('reorder-departments-form').addEventListener('submit', async event => {
  event.preventDefault();
  const status = event.target.querySelector('span');
  let items;
  try {
    items = JSON.parse(document.getElementById('desk-reorder-items').value);
  } catch (err) {
    status.textContent = ' Invalid JSON';
    return;
  }
  await submitOrgCommand(event.target, '/api/v1/org/departments/reorder', {items}, 'Departments reordered.');
});
document.getElementById('default-floorplan-btn').addEventListener('click', async () => {
  const status = document.getElementById('default-floorplan-status');
  const res = await fetch('/api/v1/floorplans/default', {
    method: 'POST',
    headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'desk-floor-default-' + Date.now()},
    body: JSON.stringify({payload: {}})
  });
  status.textContent = res.ok ? ' Default floorplan created.' : ' ' + await res.text();
  if (res.ok) load();
});
document.getElementById('staffing-scan-btn').addEventListener('click', async () => {
  const status = document.getElementById('staffing-scan-status');
  const res = await fetch('/api/v1/staffing-proposals/scan', {
    method: 'POST',
    headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'desk-staffing-scan-' + Date.now()},
    body: JSON.stringify({payload: {}})
  });
  status.textContent = res.ok ? ' Scan complete.' : ' ' + await res.text();
  if (res.ok) load();
});
function renderCrossDept(items) {
  const list = document.getElementById('cross-dept-list');
  list.innerHTML = '';
  if (!(items || []).length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No cross-department requests.';
    list.appendChild(li);
    return;
  }
  (items || []).forEach(item => {
    const li = document.createElement('li');
    li.appendChild(document.createTextNode(
      item.id.slice(0, 8) + ' — ' + item.requesting_department_id + ' → ' +
      item.delivering_department_id + ' — ' + item.status + ' — ' + item.subject + ' '));
    if (item.status === 'pending_acceptance') {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chip';
      btn.textContent = 'Accept';
      btn.addEventListener('click', async () => {
        const res = await fetch('/api/v1/cross-department-requests/' + item.id + '/accept', {
          method: 'POST',
          headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'xd-accept-' + item.id},
          body: JSON.stringify({payload: {}})
        });
        if (!res.ok) { alert(await res.text()); return; }
        load();
      });
      li.appendChild(btn);
    }
    list.appendChild(li);
  });
}
function renderPromotions(items) {
  const list = document.getElementById('promotion-list');
  list.innerHTML = '';
  if (!(items || []).length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No pending promotions.';
    list.appendChild(li);
    return;
  }
  items.forEach(promotion => {
    const li = document.createElement('li');
    li.appendChild(document.createTextNode(
      promotion.employee_id + ' — ' + promotion.from_level + ' → ' +
      promotion.to_level + ' — ' + promotion.status + ' '));
    ['approved', 'rejected'].forEach(decision => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'chip';
      button.textContent = decision === 'approved' ? 'Approve' : 'Reject';
      button.addEventListener('click', async () => {
        const res = await fetch(
          '/api/v1/promotions/' + promotion.id + '/decision',
          {
            method: 'POST',
            headers: {...headers, 'Content-Type': 'application/json',
              'Idempotency-Key': 'desk-promo-' + promotion.id + '-' + decision},
            body: JSON.stringify({payload: {decision}})
          }
        );
        if (!res.ok) { alert(await res.text()); return; }
        load();
      });
      li.appendChild(button);
    });
    list.appendChild(li);
  });
}
document.getElementById('cross-dept-create-form').addEventListener('submit', async event => {
  event.preventDefault();
  const dueLocal = document.getElementById('xd-due').value;
  const dueAt = dueLocal ? new Date(dueLocal).toISOString() : '';
  await submitOrgCommand(event.target, '/api/v1/cross-department-requests', {
    project_id: document.getElementById('xd-project').value.trim(),
    requesting_department_id: document.getElementById('xd-requesting').value.trim(),
    delivering_department_id: document.getElementById('xd-delivering').value.trim(),
    subject: document.getElementById('xd-subject').value.trim(),
    brief: document.getElementById('xd-brief').value.trim(),
    acceptance_criteria: document.getElementById('xd-accept').value.trim(),
    budget_owner: document.getElementById('xd-budget-owner').value.trim(),
    budget_cents: Number(document.getElementById('xd-budget').value),
    due_at: dueAt,
    escalation_path: document.getElementById('xd-escalation').value.trim()
  }, 'Cross-department request created.');
});
document.getElementById('division-proposal-form').addEventListener('submit', async event => {
  event.preventDefault();
  await submitOrgCommand(event.target, '/api/v1/divisions/proposals', {
    pack_id: document.getElementById('division-pack-id').value.trim(),
    name: document.getElementById('division-name').value.trim(),
    mode: document.getElementById('division-mode').value
  }, 'Division proposed.');
});
document.getElementById('objective-create-form').addEventListener('submit', async event => {
  event.preventDefault();
  const rawTarget = document.getElementById('objective-target').value.trim();
  let target = {};
  try {
    if (rawTarget) target = JSON.parse(rawTarget);
  } catch (error) {
    event.target.querySelector('span').textContent = ' Target must be valid JSON.';
    return;
  }
  const dueValue = document.getElementById('objective-due-at').value;
  const payload = {
    title: document.getElementById('objective-title').value.trim(),
    due_at: new Date(dueValue).toISOString(),
    target
  };
  const divisionId = document.getElementById('objective-division').value.trim();
  if (divisionId) payload.division_id = divisionId;
  await submitOrgCommand(
    event.target, '/api/v1/objectives', payload, 'Objective created.');
});
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
    detail.room.id + ' — ' + detail.room.status + ' — '
      + (detail.room.room_type || detail.room.source_project),
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
async function openWorkerCard(employeeId) {
  const panel = document.getElementById('worker-card');
  const facts = document.getElementById('worker-facts');
  const [res, ladderRes] = await Promise.all([
    fetch('/api/v1/workers/' + encodeURIComponent(employeeId) + '/card', {headers}),
    fetch('/api/v1/employees/' + encodeURIComponent(employeeId) + '/ladder', {headers})
  ]);
  const card = await res.json();
  const ladder = ladderRes.ok ? await ladderRes.json() : null;
  panel.hidden = false;
  facts.innerHTML = '';
  if (!res.ok) {
    document.getElementById('worker-name').textContent = 'Worker';
    document.getElementById('worker-headline').textContent =
      card.detail || 'Worker not found';
    return;
  }
  document.getElementById('worker-name').textContent =
    card.identity.display_name;
  document.getElementById('worker-headline').textContent =
    card.identity.headline || card.identity.position_id;
  const lines = [
    'Viewpoint: ' + (card.viewpoint || 'not set'),
    'Strengths: ' + listed(card.strengths, value => value),
    'Skills: ' + listed(card.skills, skill => skill.name),
    'Positions: ' + listed(
      card.position_assignments, assignment => assignment.title),
    'Career level: ' + (
      ladder && ladder.current_level
        ? ladder.current_level.title + ' (L' + ladder.current_level.level_index + ')'
        : 'not assigned'),
    'Sprite: ' + (card.sprite ? card.sprite.sprite_set : 'neutral placeholder')
  ];
  lines.forEach(line => {
    const li = document.createElement('li');
    li.textContent = line;
    facts.appendChild(li);
  });
  location.hash = 'worker-card';
}
function renderHeadInbox(items) {
  const list = document.getElementById('head-inbox-list');
  list.innerHTML = '';
  if (!items.length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No open head dispatches.';
    list.appendChild(li);
    return;
  }
  items.forEach(dispatch => {
    const li = document.createElement('li');
    li.appendChild(document.createTextNode(
      dispatch.project_id + ' · ' + dispatch.department_id + ' · ' + dispatch.status
      + ' · budget ' + dispatch.budget_cents + '¢'));
    if (dispatch.status === 'queued_for_head') {
      const form = document.createElement('form');
      form.className = 'compact';
      form.innerHTML = '<label>Assignee principal<input name="assignee" required></label>'
        + '<label>Action<input name="action" required></label>'
        + '<label>Cost (¢)<input name="cost" type="number" min="0" required></label>'
        + '<button class="chip" type="submit">Assign</button><span class="muted"></span>';
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const fields = new FormData(form);
        const res = await fetch(
          '/api/v1/dispatches/' + encodeURIComponent(dispatch.id) + '/assign',
          {
            method: 'POST',
            headers: {...headers, 'Content-Type': 'application/json', 'Idempotency-Key': 'desk-assign-' + dispatch.id},
            body: JSON.stringify({payload: {
              assignee: fields.get('assignee'),
              action: fields.get('action'),
              cost_cents: Number(fields.get('cost'))
            }})
          }
        );
        form.querySelector('span').textContent = res.ok ? ' Assigned.' : ' ' + await res.text();
        if (res.ok) load();
      });
      li.appendChild(form);
    }
    list.appendChild(li);
  });
}
function renderStaffingProposals(items) {
  const list = document.getElementById('staffing-proposal-list');
  list.innerHTML = '';
  if (!items.length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No pending staffing proposals.';
    list.appendChild(li);
    return;
  }
  items.forEach(proposal => {
    const li = document.createElement('li');
    li.appendChild(document.createTextNode(
      proposal.kind + ' · ' + proposal.position_id + ' · '
      + proposal.cost_estimate_cents + '¢ · ' + proposal.rationale + ' '));
    ['approved', 'rejected'].forEach(decision => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'chip';
      button.textContent = decision === 'approved' ? 'Approve' : 'Reject';
      button.addEventListener('click', async () => {
        const res = await fetch(
          '/api/v1/staffing-proposals/' + proposal.id + '/decision',
          {
            method: 'POST',
            headers: {...headers, 'Content-Type': 'application/json',
              'Idempotency-Key': 'desk-staffing-' + proposal.id + '-' + decision},
            body: JSON.stringify({payload: {decision}})
          }
        );
        if (!res.ok) { alert(await res.text()); return; }
        load();
      });
      li.appendChild(button);
    });
    list.appendChild(li);
  });
}
function renderDivisions(items) {
  const list = document.getElementById('division-list');
  list.innerHTML = '';
  if (!items.length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No division proposals.';
    list.appendChild(li);
    return;
  }
  items.forEach(division => {
    const li = document.createElement('li');
    const label = document.createElement('span');
    label.textContent = division.name + ' — ' + division.industry_pack_id +
      ' — ' + division.mode + ' — ' + division.status;
    li.appendChild(label);
    if (division.status === 'proposed') {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'chip';
      button.textContent = 'Activate (CEO)';
      button.style.marginLeft = '0.5rem';
      button.addEventListener('click', async () => {
        const res = await fetch('/api/v1/divisions/' + division.id + '/activate', {
          method: 'POST',
          headers: {...headers, 'Content-Type': 'application/json',
            'Idempotency-Key': 'desk-division-activate-' + division.id},
          body: JSON.stringify({payload: {}})
        });
        if (!res.ok) { alert(await res.text()); return; }
        load();
      });
      li.appendChild(button);
    }
    list.appendChild(li);
  });
}
function renderObjectives(items) {
  const list = document.getElementById('objective-list');
  list.innerHTML = '';
  if (!items.length) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'No objectives.';
    list.appendChild(li);
    return;
  }
  items.forEach(objective => {
    const li = document.createElement('li');
    li.appendChild(document.createTextNode(
      objective.title + ' — due ' + objective.due_at + ' — ' + objective.status + ' '));
    if (objective.status === 'open') {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'chip';
      button.textContent = 'Close';
      button.addEventListener('click', async () => {
        const res = await fetch('/api/v1/objectives/' + objective.id + '/close', {
          method: 'POST',
          headers: {...headers, 'Content-Type': 'application/json',
            'Idempotency-Key': 'desk-objective-close-' + objective.id},
          body: JSON.stringify({payload: {}})
        });
        if (!res.ok) { alert(await res.text()); return; }
        load();
      });
      li.appendChild(button);
    }
    list.appendChild(li);
  });
}
async function load() {
  const status = await fetch('/api/v1/company', {headers});
  document.getElementById('status-json').textContent = await status.text();
  const hq = await fetch('/api/v1/headquarters', {headers});
  const data = await hq.json();
  headquartersRooms = data.rooms || [];
  const list = document.getElementById('room-list');
  list.innerHTML = '';
  const hasFloorplan = (data.rooms || []).some(room => !!room.floorplan_id);
  const requirements = document.getElementById('unmet-requirements');
  requirements.innerHTML = '';
  (data.unmet_requirements || []).forEach(gap => {
    const chip = document.createElement('span');
    chip.className = 'chip tag-warning';
    chip.textContent = gap.department_id + ': needs ' + gap.required_room_type
      + ' (' + gap.actual_capacity + '/' + gap.min_capacity + ')';
    requirements.appendChild(chip);
  });
  (data.rooms||[]).forEach(room => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.className = 'room';
    btn.type = 'button';
    btn.textContent = room.id + ' — ' + (room.label || room.status)
      + ' — ' + (room.room_type || room.source_project);
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
  const projects = await fetch('/api/v1/projects', {headers});
  const pj = await projects.json();
  fill('project-list', pj.projects||[], p => p.id + ' — ' + (p.brief || p.status || ''));
  const localReposEl = document.getElementById('local-repo-list');
  localReposEl.innerHTML = '';
  try {
    const lr = await fetch('/api/v1/local-repos', {headers});
    const lj = await lr.json();
    if (!lr.ok) {
      const li = document.createElement('li');
      li.textContent = 'local-repos unavailable';
      localReposEl.appendChild(li);
    } else if (!(lj.candidates||[]).length) {
      const li = document.createElement('li');
      li.className = 'muted';
      li.textContent = 'No folders under ' + (lj.root || 'local repos/');
      localReposEl.appendChild(li);
    } else {
      (lj.candidates||[]).forEach(c => {
        const li = document.createElement('li');
        const label = document.createElement('span');
        label.textContent = c.id + ' — ' + (c.enrolled ? 'enrolled' : 'not enrolled')
          + (c.has_git ? ' · git' : '')
          + (c.remote_url ? ' · ' + c.remote_url : '');
        li.appendChild(label);
        if (!c.enrolled) {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'chip';
          btn.textContent = 'Enroll';
          btn.style.marginLeft = '0.5rem';
          btn.addEventListener('click', async () => {
            const res = await fetch('/api/v1/projects', {
              method: 'POST',
              headers: Object.assign({'Content-Type': 'application/json', 'Idempotency-Key': 'local-enroll-' + c.id}, headers),
              body: JSON.stringify({payload: {id: c.id, brief: c.remote_url || ('Local repo ' + c.path)}}),
            });
            if (!res.ok) { alert(await res.text()); return; }
            load();
          });
          li.appendChild(btn);
        }
        localReposEl.appendChild(li);
      });
    }
  } catch (e) {
    const li = document.createElement('li');
    li.textContent = 'local-repos unavailable';
    localReposEl.appendChild(li);
  }
  const org = await fetch('/api/v1/org', {headers});
  const oj = await org.json();
  fill('org-list', oj.departments||[], d => {
    const seat = d.seat || {};
    const origin = d.origin || 'seed';
    const status = d.status || (d.initially_active ? 'active' : 'dormant');
    const roster = listed(d.assignments, a => a.principal_id + ' (' + a.position_id + ')');
    return d.id + ' — ' + d.name + ' — ' + status + ' (' + origin + ') — seat ' +
      (seat.status || 'vacant') + ' — ' + (seat.principal_id || 'vacant') +
      ' — order ' + (d.display_order ?? 0) + ' — roster: ' + roster;
  });
  const packs = await fetch('/api/v1/industry-packs', {headers});
  const packsj = await packs.json();
  fill('industry-pack-list', packsj.industry_packs || [], pack =>
    pack.id + ' — ' + pack.industry + ' — minimal ' +
    pack.minimal_departments.length + ' / full ' + pack.full_departments.length);
  const divisions = await fetch('/api/v1/divisions', {headers});
  const divisionsj = await divisions.json();
  renderDivisions(divisionsj.divisions || []);
  const scorecard = await fetch('/api/v1/scorecard', {headers});
  const scorecardj = await scorecard.json();
  document.getElementById('scorecard-metrics').textContent =
    JSON.stringify(scorecardj.metrics || {}, null, 2);
  const objectives = await fetch('/api/v1/objectives', {headers});
  const objectivesj = await objectives.json();
  renderObjectives(objectivesj.items || []);
  const headInbox = await fetch('/api/v1/inbox/head', {headers});
  const hij = await headInbox.json();
  renderHeadInbox(hij.items || []);
  const people = await fetch('/api/v1/hr/development', {headers});
  const peoplej = await people.json();
  fill('people-list', peoplej.employees || peoplej.assignments || [], p => (p.display_name || p.employee_id || p.id) + ' — ' + (p.position_id || p.status || ''));
  const promotions = await fetch('/api/v1/promotions?status=pending', {headers});
  const promotionsj = await promotions.json();
  renderPromotions(promotionsj.items || []);
  const staffing = await fetch(
    '/api/v1/staffing-proposals?status=pending', {headers});
  const staffingj = await staffing.json();
  renderStaffingProposals(staffingj.items || []);
  const crossDept = await fetch('/api/v1/cross-department-requests', {headers});
  const crossDeptj = await crossDept.json();
  renderCrossDept(crossDeptj.items || []);
  const briefs = await fetch('/api/v1/impact-briefs', {headers});
  const bj = await briefs.json();
  fill('intelligence-list', bj.briefs||[], b => {
    let summary = '';
    try { summary = (JSON.parse(b.body||'{}').affected_summary) || ''; } catch (e) { summary = ''; }
    return (b.id||'').slice(0,12) + ' — ' + (b.status||'') + (summary ? ' — ' + summary : '');
  });
  const dash = await fetch('/api/v1/dashboard', {headers});
  const dashj = await dash.json();
  const company = dashj.company || {};
  document.getElementById('metric-projects').textContent = pad((pj.projects||[]).length);
  document.getElementById('metric-decisions').textContent = pad((ij.items||[]).length);
  document.getElementById('metric-departments').textContent = pad((oj.departments||[]).length);
  document.getElementById('budget-json').textContent = JSON.stringify({
    simulated_spend_cents: company.simulated_spend_cents,
    billed_cost_cents: company.billed_cost_cents,
    revenue_cents: company.revenue_cents,
    reserved_cents: company.reserved_cents,
    note: 'Simulated credits stay separate from billed cost and revenue'
  });
  const svg = document.getElementById('floor');
  svg.innerHTML = '';
  const iso = document.getElementById('iso');
  iso.innerHTML = '';
  function ns(name) { return document.createElementNS('http://www.w3.org/2000/svg', name); }
  if (hasFloorplan) {
    const plan = (data.floorplans || []).find(
      item => item.id === data.rooms[0].floorplan_id) || data.floorplans[0];
    const inset = 4;
    const cellW = (200 - inset * 2) / plan.grid_cols;
    const cellH = (80 - inset * 2) / plan.grid_rows;
    (data.rooms || []).filter(room => room.floorplan_id === plan.id).forEach(room => {
      const x = inset + room.grid_x * cellW;
      const y = inset + room.grid_y * cellH;
      const r = ns('rect');
      r.setAttribute('x', x); r.setAttribute('y', y);
      r.setAttribute('width', room.width * cellW);
      r.setAttribute('height', room.height * cellH);
      r.setAttribute('fill', '#1d4ed8'); r.setAttribute('stroke', '#93c5fd');
      r.setAttribute('data-room-id', room.id);
      r.addEventListener('click', () => openRoom(room.id));
      svg.appendChild(r);
      const t = ns('text');
      t.setAttribute('x', x + 2); t.setAttribute('y', y + Math.min(9, cellH - 1));
      t.setAttribute('fill', '#eee'); t.setAttribute('font-size', '5');
      t.textContent = room.room_type;
      svg.appendChild(t);
      (room.workers || []).forEach((worker, index) => {
        const marker = ns('circle');
        marker.setAttribute('cx', x + 6 + index * 7);
        marker.setAttribute('cy', y + room.height * cellH - 6);
        marker.setAttribute('r', '3');
        marker.setAttribute(
          'fill', worker.sprite ? '#34d399' : '#9aa8c0');
        marker.setAttribute('stroke', '#e8eef8');
        marker.setAttribute('data-worker-id', worker.employee_id);
        marker.setAttribute('aria-label', worker.display_name);
        marker.addEventListener('click', event => {
          event.stopPropagation();
          openWorkerCard(worker.employee_id);
        });
        svg.appendChild(marker);
      });
    });
    setHqView('plan');
  }
  const expansionRooms = hasFloorplan ? (data.expansions || []) : (data.rooms || []);
  expansionRooms.forEach((room, i) => {
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
  if (!hasFloorplan) setHqView('iso');
  await loadActivity();
}
load().catch(err => { document.getElementById('status-json').textContent = String(err); });
setInterval(loadActivity, 10000);
async function loadDiagnostics() {
  const host = document.getElementById('diag-blocks');
  host.innerHTML = 'Loading…';
  const probes = [
    ['health', '/api/v1/health'],
    ['workers', '/api/v1/workers/status'],
    ['model', '/api/v1/model/status'],
    ['github', '/api/v1/github/status'],
    ['push', '/api/v1/push/status'],
    ['chatdev', '/api/v1/chatdev/status'],
    ['feeds', '/api/v1/feeds'],
    ['slos', '/api/v1/slos'],
    ['local-repos', '/api/v1/local-repos'],
  ];
  const parts = await Promise.all(probes.map(async ([label, path]) => {
    try {
      const res = await fetch(path, {headers});
      const text = await res.text();
      let body = text;
      try { body = JSON.stringify(JSON.parse(text), null, 2); } catch (e) {}
      return {label, ok: res.ok, body: res.ok ? body : (res.status + ': ' + text)};
    } catch (e) {
      return {label, ok: false, body: String(e)};
    }
  }));
  host.innerHTML = '';
  parts.forEach(p => {
    const wrap = document.createElement('div');
    wrap.style.marginTop = '0.75rem';
    const h = document.createElement('h3');
    h.textContent = p.label + (p.ok ? '' : ' (unavailable)');
    const pre = document.createElement('pre');
    pre.textContent = p.body;
    wrap.appendChild(h);
    wrap.appendChild(pre);
    host.appendChild(wrap);
  });
}
document.getElementById('diag-refresh').addEventListener('click', () => loadDiagnostics());
loadDiagnostics().catch(() => {});
</script>
</body>
</html>
"""


class Command(BaseModel):
    expected_policy_version: int | None = None
    payload: dict = Field(default_factory=dict)


def _json(data, code=200):
    return JSONResponse(status_code=code, content=data)


def create_app(company: Company, *, rate_limit=None) -> FastAPI:
    app = FastAPI(title="FS-Corporation", version=__version__)
    app.state.company = company
    if rate_limit is None:
        rate_limit = RateLimitPolicy(
            authenticated_limit=int(os.environ.get("FS_CORP_RATE_LIMIT_AUTH") or "120"),
            unauthenticated_limit=int(os.environ.get("FS_CORP_RATE_LIMIT_UNAUTH") or "60"),
            window_sec=float(os.environ.get("FS_CORP_RATE_LIMIT_WINDOW_SEC") or "60"),
        )
    limiter = RateLimiter(policy=coerce_policy(rate_limit))
    app.state.rate_limiter = limiter
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

        def execute():
            try:
                result, code = handler()
            except PermissionError as exc:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
            except NotImplementedError as exc:
                raise HTTPException(status_code=501, detail=str(exc)) from exc
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
            return result, code, wrapped

        if key:
            def work():
                _result, code, wrapped = execute()
                return wrapped, code, json.dumps(wrapped)

            try:
                outcome = company.run_idempotent(
                    key, ident["principal_id"], req_hash, work)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            if outcome["replay"]:
                return _json(json.loads(outcome["response_body"]), outcome["status_code"])
            return _json(outcome["result"], outcome["status_code"])

        _result, code, wrapped = execute()
        return _json(wrapped, code)

    def wrapped_corr(result):
        if isinstance(result, dict):
            return result.get("id") or result.get("task_id") or result.get("event_correlation_id")
        return None

    @app.get("/", response_class=HTMLResponse)
    def desk_page():
        return DESK_HTML

    @app.get("/desk", response_class=HTMLResponse)
    def desk_page_alias():
        # fs-dev Caddy serves the companion at /; /desk keeps the CEO desk reachable on HTTPS.
        return DESK_HTML

    @app.get("/api/v1/health")
    def health():
        return {"ok": True, "version": app.version, "db": company.db_path}

    @app.get("/api/v1/session")
    def session(authorization: str | None = Header(default=None)):
        """Scopes for the presented token, so a client never has to guess them.

        Deliberately requires authentication only: a read-only device must be
        able to learn that it is read-only.
        """
        ident = principal(authorization)
        raw = ident.get("scopes")
        if raw is None:
            scopes = []
        elif isinstance(raw, str):
            scopes = json.loads(raw)
        else:
            scopes = list(raw)
        principal_id = ident["principal_id"]
        access_level = None
        if principal_id.startswith("companion-"):
            access_level = principal_id[len("companion-"):].rsplit("-", 1)[0]
        return {
            "principal_id": principal_id,
            "kind": ident["kind"],
            "access_level": access_level,
            "scopes": scopes,
        }

    @app.get("/api/v1/company")
    def get_company(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.status() | {"paused": company.db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0]}

    @app.get("/api/v1/settings")
    def settings(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.list_company_settings()

    @app.patch("/api/v1/settings")
    def patch_settings(
            body: Command, authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        unknown = payload.keys() - {"updates"}
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unknown fields: {sorted(unknown)}")
        return run(
            ident, idempotency_key, payload,
            lambda: (
                company.patch_company_settings(
                    ident["principal_id"], payload.get("updates")), 200),
        )

    @app.post("/api/v1/settings/reset")
    def reset_settings(
            body: Command, authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        unknown = payload.keys() - {"keys", "all_overlay"}
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unknown fields: {sorted(unknown)}")
        return run(
            ident, idempotency_key, payload,
            lambda: (
                company.reset_company_settings(
                    ident["principal_id"],
                    keys=payload.get("keys"),
                    all_overlay=payload.get("all_overlay", False),
                ),
                200,
            ),
        )

    @app.get("/api/v1/settings/secrets-status")
    def settings_secrets_status(
            authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.secrets_status()

    @app.get("/api/v1/activity")
    def activity(status: str = "open",
                 authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        try:
            return company.list_activity(status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/scorecard")
    def scorecard(period_start: str | None = None, period_end: str | None = None,
                  authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        try:
            return company.compute_scorecard(period_start, period_end)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/model-profiles")
    def model_profiles(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return {"profiles": company.list_model_profiles()}

    @app.get("/api/v1/benchmarks")
    def benchmarks(role: str | None = None, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return {"items": company.list_benchmark_results(role=role)}

    @app.get("/api/v1/objectives")
    def objectives(status: str | None = None,
                   authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        try:
            return company.list_objectives(status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/objectives")
    def create_objective(
            body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident, idempotency_key, payload,
            lambda: (
                company.set_objective(ident["principal_id"], **payload), 200))

    @app.post("/api/v1/objectives/{objective_id}/close")
    def close_objective(
            objective_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        if payload:
            raise HTTPException(
                status_code=422, detail=f"Unknown fields: {sorted(payload)}")
        return run(
            ident, idempotency_key, {"objective_id": objective_id},
            lambda: (
                company.close_objective(ident["principal_id"], objective_id), 200))

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

    @app.post("/api/v1/ops/idempotency/prune")
    def idempotency_prune(
            body: Command, authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "company.pause")
        payload = envelope(ident, body)
        unknown = payload.keys() - {"older_than_days"}
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown fields: {sorted(unknown)}")
        return run(
            ident, idempotency_key, payload,
            lambda: (company.prune_idempotency_keys(
                ident["principal_id"], payload.get("older_than_days")), 200),
        )

    @app.get("/api/v1/departments")
    def departments(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        rows = [dict(r) for r in company.db.execute("SELECT id,name,head_title,initially_active FROM departments ORDER BY id")]
        return {"departments": rows}

    @app.get("/api/v1/industry-packs")
    def industry_packs(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        return company.list_industry_packs()

    @app.get("/api/v1/divisions")
    def divisions(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        return company.list_divisions()

    @app.post("/api/v1/divisions/proposals")
    def propose_division(
            body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident, idempotency_key, payload,
            lambda: (
                company.propose_division(ident["principal_id"], **payload), 200))

    @app.post("/api/v1/divisions/{division_id}/activate")
    def activate_division(
            division_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        if payload:
            raise HTTPException(
                status_code=422, detail=f"Unknown fields: {sorted(payload)}")
        return run(
            ident, idempotency_key, {"division_id": division_id},
            lambda: (
                company.activate_division(ident["principal_id"], division_id), 200))

    @app.post("/api/v1/divisions/{division_id}/deactivate")
    def deactivate_division(
            division_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        if payload:
            raise HTTPException(
                status_code=422, detail=f"Unknown fields: {sorted(payload)}")
        return run(
            ident, idempotency_key, {"division_id": division_id},
            lambda: (
                company.deactivate_division(ident["principal_id"], division_id), 200))

    @app.get("/api/v1/org")
    def org(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        return company.list_org()

    @app.get("/api/v1/inbox/head")
    def head_inbox(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        return company.list_head_inbox(ident["principal_id"])

    @app.get("/api/v1/cross-department-requests")
    def cross_department_requests(
            authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        return company.list_cross_dept_requests(ident["principal_id"])

    @app.post("/api/v1/cross-department-requests")
    def cross_department_request_create(
            body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident,
            idempotency_key,
            payload,
            lambda: (
                company.create_cross_dept_request(
                    ident["principal_id"], **payload),
                200,
            ),
        )

    @app.post("/api/v1/cross-department-requests/{request_id}/accept")
    def cross_department_request_accept(
            request_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident,
            idempotency_key,
            payload | {"request_id": request_id},
            lambda: (
                company.accept_cross_dept_request(
                    ident["principal_id"], request_id),
                200,
            ),
        )

    @app.post("/api/v1/dispatches/{dispatch_id}/assign")
    def dispatch_assign(
            dispatch_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        command_payload = payload | {"dispatch_id": dispatch_id}
        return run(
            ident,
            idempotency_key,
            command_payload,
            lambda: (
                company.assign_dispatch(
                    ident["principal_id"],
                    dispatch_id,
                    payload["assignee"],
                    action=payload["action"],
                    cost_cents=payload["cost_cents"],
                ),
                200,
            ),
        )

    @app.post("/api/v1/org/heads")
    def org_heads(body: Command, authorization: str | None = Header(default=None),
                  idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)

        def go():
            if payload.get("vacate"):
                return company.vacate_head(
                    ident["principal_id"], payload["department_id"]), 200
            return company.appoint_head(
                ident["principal_id"], payload["department_id"], payload["principal_id"]), 200

        return run(ident, idempotency_key, payload, go)

    @app.post("/api/v1/org/assignments")
    def org_assignments(body: Command, authorization: str | None = Header(default=None),
                        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)

        def go():
            if payload.get("release"):
                return company.release_position(
                    ident["principal_id"], payload["assignment_id"]), 200
            return company.assign_position(
                ident["principal_id"], payload["position_id"], payload["principal_id"],
                payload.get("reports_to_seat_id")), 200

        return run(ident, idempotency_key, payload, go)

    @app.post("/api/v1/org/departments")
    def org_departments_create(body: Command, authorization: str | None = Header(default=None),
                               idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (
            company.create_department(
                ident["principal_id"],
                department_id=payload.get("id") or payload.get("department_id"),
                name=payload["name"],
                head_title=payload["head_title"],
                mission=payload["mission"],
                measures=payload.get("measures") or [],
                room_type=payload["room_type"],
                initially_active=bool(payload.get("initially_active", False)),
                default_model_profile=payload.get("default_model_profile", "mock-text"),
                parent_department_id=payload.get("parent_department_id"),
                display_order=payload.get("display_order"),
            ), 200))

    @app.patch("/api/v1/org/departments/{department_id}")
    def org_departments_update(department_id: str, body: Command,
                               authorization: str | None = Header(default=None),
                               idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        reason = payload.pop("reason", "update")
        payload.pop("id", None)
        payload.pop("department_id", None)
        return run(ident, idempotency_key, payload | {"department_id": department_id}, lambda: (
            company.update_department(
                ident["principal_id"], department_id, reason=reason, **payload), 200))

    @app.post("/api/v1/org/departments/{department_id}/retire")
    def org_departments_retire(department_id: str, body: Command,
                               authorization: str | None = Header(default=None),
                               idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"department_id": department_id}, lambda: (
            company.retire_department(ident["principal_id"], department_id), 200))

    @app.post("/api/v1/org/departments/reorder")
    def org_departments_reorder(body: Command, authorization: str | None = Header(default=None),
                                idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (
            company.reorder_departments(ident["principal_id"], payload["items"]), 200))

    @app.post("/api/v1/org/positions")
    def org_positions_create(body: Command, authorization: str | None = Header(default=None),
                             idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (
            company.create_position(
                ident["principal_id"],
                department_id=payload["department_id"],
                title=payload["title"],
                display_order=payload.get("display_order"),
            ), 200))

    @app.patch("/api/v1/org/positions/{position_id:path}")
    def org_positions_update(position_id: str, body: Command,
                             authorization: str | None = Header(default=None),
                             idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        fields = {k: payload[k] for k in ("title", "display_order", "status") if k in payload}
        return run(ident, idempotency_key, payload | {"position_id": position_id}, lambda: (
            company.update_position(ident["principal_id"], position_id, **fields), 200))

    @app.post("/api/v1/projects/{project_id}/departments/{department_id}/activate")
    def activate_project_department(
            project_id: str, department_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        command_payload = payload | {
            "project_id": project_id,
            "department_id": department_id,
        }
        return run(
            ident,
            idempotency_key,
            command_payload,
            lambda: (company.activate_department_for_project(
                ident["principal_id"], project_id, department_id), 200),
        )

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

    @app.get("/api/v1/local-repos")
    def local_repos(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.list_local_repos()

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
        try:
            return {"subscriptions": company.list_push_subscriptions(ident["principal_id"])}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

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
                ident["principal_id"], project_id, payload["brief"],
                payload["department_budgets"], payload["acceptance_criteria"],
                payload.get("due_at"))}, 200))

    @app.get("/api/v1/projects/{project_id}/dispatch-options")
    def dispatch_options(project_id: str, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "project.enroll")
        try:
            return company.dispatch_options(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/projects/{project_id}/dispatch-recommend")
    def dispatch_recommend(
            project_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "project.enroll")
        payload = envelope(ident, body)
        use_live = payload.get("use_live", True)
        unknown = payload.keys() - {"use_live"}
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown fields: {sorted(unknown)}")
        return run(
            ident, idempotency_key, payload | {"project_id": project_id},
            lambda: (company.recommend_dispatch(
                ident["principal_id"], project_id, use_live=bool(use_live)), 200),
        )

    @app.get("/api/v1/events/stream")
    async def events_stream(cursor: int = 0, authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "audit.read")
        idle = float(os.environ.get("FS_CORP_SSE_IDLE_SEC", "1"))

        async def generate():
            pos = cursor
            while True:
                page = company.events_page(pos, 20)
                for item in page["items"]:
                    pos = item["seq"]
                    frame = {
                        "seq": item["seq"], "kind": item["kind"], "at": item["at"]}
                    activity = company.activity_for_event(item["seq"])
                    if activity and activity.get("room_id"):
                        frame["room_id"] = activity["room_id"]
                    yield f"data: {json.dumps(frame)}\n\n"
                if idle <= 0:
                    return
                if not page["items"]:
                    await asyncio.sleep(idle)
                if len(page["items"]) < 20:
                    await asyncio.sleep(idle)

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
        from company.worker_status import resolve_worker_runtime
        try:
            runtime = resolve_worker_runtime(payload.get("runtime"))
        except (ValueError, NotImplementedError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return run(ident, idempotency_key, payload | {"task_id": task_id, "runtime": runtime}, lambda: (
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

    @app.get("/api/v1/employees/{employee_id}/ladder")
    def employee_ladder(employee_id: str,
                        authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        try:
            return company.employee_ladder(employee_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/promotions")
    def promotions(status: str | None = None,
                   authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        try:
            return company.list_promotions(status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/staffing-proposals")
    def staffing_proposals(
            status: str | None = None,
            authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        try:
            return company.list_staffing_proposals(status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/staffing-proposals")
    def create_staffing_proposal(
            body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident,idempotency_key,payload,
            lambda: (
                company.create_staffing_proposal(
                    ident["principal_id"],**payload),200))

    @app.post("/api/v1/staffing-proposals/scan")
    def scan_staffing_proposals(
            body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        if payload:
            raise HTTPException(
                status_code=422,detail=f"Unknown fields: {sorted(payload)}")
        return run(
            ident,idempotency_key,payload,
            lambda: (company.scan_staffing_gaps(ident["principal_id"]),200))

    @app.post("/api/v1/staffing-proposals/{proposal_id}/decision")
    def decide_staffing_proposal(
            proposal_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident,idempotency_key,payload | {"proposal_id":proposal_id},
            lambda: (
                company.decide_staffing_proposal(
                    ident["principal_id"],proposal_id,payload["decision"]),200))

    @app.post("/api/v1/employees/{employee_id}/promotions")
    def propose_promotion(
            employee_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident, idempotency_key, payload | {"employee_id":employee_id},
            lambda: (
                company.propose_promotion(
                    ident["principal_id"],employee_id,payload.get("to_level_id")),
                200,
            ),
        )

    @app.post("/api/v1/promotions/{promotion_id}/decision")
    def decide_promotion(
            promotion_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident, idempotency_key, payload | {"promotion_id":promotion_id},
            lambda: (
                company.decide_promotion(
                    ident["principal_id"],promotion_id,payload["decision"]),
                200,
            ),
        )

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

    @app.get("/api/v1/impact-briefs")
    def list_impact_briefs(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return {"briefs": company.list_impact_briefs()}

    @app.post("/api/v1/impact-briefs")
    def create_impact_brief(body: Command, authorization: str | None = Header(default=None),
                            idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "intelligence.ingest")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload, lambda: (
            company.create_impact_brief(
                payload["signal_id"], payload["project_id"], payload["affected_summary"],
                payload["recommended_action"], payload.get("cost_cents", 0), payload["authority"]),
            200))

    @app.post("/api/v1/signals/{signal_id}/correct")
    def correct_signal(signal_id: str, body: Command, authorization: str | None = Header(default=None),
                       idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "intelligence.ingest")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"signal_id": signal_id}, lambda: (
            company.correct_signal(signal_id, payload["note"]), 200))

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

    @app.post("/api/v1/projects/{project_id}/github-assign")
    def github_assign(project_id: str, body: Command, authorization: str | None = Header(default=None),
                      idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        """Paste upstream github.com address; create/reuse same-owner {repo}-corp; enroll."""
        ident = principal(authorization)
        scoped(ident, "project.enroll")
        payload = envelope(ident, body)
        return run(ident, idempotency_key, payload | {"project_id": project_id}, lambda: (
            company.assign_github_by_address(
                ident["principal_id"], project_id, str(payload.get("upstream") or "")),
            200))

    @app.get("/api/v1/github/status")
    def github_status(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        from company.github_app import status_summary
        return status_summary()

    @app.post("/api/v1/github/webhooks")
    async def github_webhooks(
        request: Request,
        x_github_event: str | None = Header(default=None),
        x_github_delivery: str | None = Header(default=None),
        x_hub_signature_256: str | None = Header(default=None),
    ):
        """GitHub App webhook ingress. Auth is HMAC only; no bearer token."""
        from company.github_webhooks import WebhookError, parse_and_verify
        body = await request.body()
        try:
            event, delivery_id, payload = parse_and_verify(
                body=body,
                event=x_github_event,
                delivery_id=x_github_delivery,
                signature_header=x_hub_signature_256,
            )
        except WebhookError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        return company.ingest_github_webhook(event, delivery_id, payload)

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

    @app.get("/api/v1/chatdev/status")
    def chatdev_status(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        from company.chatdev_runtime import status_summary
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

    @app.get("/api/v1/floorplans")
    def floorplans(authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        return company.list_floorplans()

    @app.get("/api/v1/workers/{employee_id}/card")
    def worker_card(
            employee_id: str,
            authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "organization.read")
        try:
            return company.worker_card(employee_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/workers/{employee_id}/sprite")
    def worker_sprite(
            employee_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident, idempotency_key, payload | {"employee_id": employee_id},
            lambda: (
                company.set_worker_sprite(
                    ident["principal_id"], employee_id, **payload), 200))

    @app.patch("/api/v1/workers/{employee_id}/profile")
    def worker_profile(
            employee_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident, idempotency_key, payload | {"employee_id": employee_id},
            lambda: (
                company.update_worker_profile(
                    ident["principal_id"], employee_id, **payload), 200))

    @app.get("/api/v1/floorplans/{floorplan_id}")
    def floorplan_detail(
            floorplan_id: str,
            authorization: str | None = Header(default=None)):
        ident = principal(authorization)
        scoped(ident, "company.read")
        try:
            return company.get_floorplan(floorplan_id)
        except LookupError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/floorplans")
    def floorplan_create(
            body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        return run(
            ident, idempotency_key, payload,
            lambda: (
                company.create_floorplan(ident["principal_id"], **payload), 200))

    @app.post("/api/v1/floorplans/{floorplan_id}/rooms")
    def floorplan_room_create(
            floorplan_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        command_payload = payload | {"floorplan_id": floorplan_id}
        return run(
            ident, idempotency_key, command_payload,
            lambda: (
                company.upsert_floorplan_room(
                    ident["principal_id"], floorplan_id, **payload), 200))

    @app.patch("/api/v1/floorplans/{floorplan_id}/rooms/{room_id}")
    def floorplan_room_update(
            floorplan_id: str, room_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        command_payload = payload | {
            "floorplan_id": floorplan_id, "room_id": room_id}

        def update():
            room = company._floorplan_room(room_id)
            if room["floorplan_id"] != floorplan_id:
                raise ValueError("Room belongs to another floorplan")
            if set(payload) == {"grid_x", "grid_y"}:
                result = company.move_room(
                    ident["principal_id"], room_id,
                    payload["grid_x"], payload["grid_y"])
            else:
                result = company.upsert_floorplan_room(
                    ident["principal_id"], floorplan_id,
                    **(payload | {"id": room_id}))
            return result, 200

        return run(ident, idempotency_key, command_payload, update)

    @app.delete("/api/v1/floorplans/{floorplan_id}/rooms/{room_id}")
    def floorplan_room_delete(
            floorplan_id: str, room_id: str, body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        command_payload = payload | {
            "floorplan_id": floorplan_id, "room_id": room_id}

        def remove():
            room = company._floorplan_room(room_id)
            if room["floorplan_id"] != floorplan_id:
                raise ValueError("Room belongs to another floorplan")
            return company.remove_room(ident["principal_id"], room_id), 200

        return run(ident, idempotency_key, command_payload, remove)

    @app.post("/api/v1/floorplans/default")
    def floorplan_default(
            body: Command,
            authorization: str | None = Header(default=None),
            idempotency_key: str | None = Header(
                default=None, alias="Idempotency-Key")):
        ident = principal(authorization)
        scoped(ident, "organization.write")
        payload = envelope(ident, body)
        unknown = set(payload) - {"division_id"}
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unknown fields: {sorted(unknown)}")
        return run(
            ident, idempotency_key, payload,
            lambda: (
                company.default_floorplan_for(
                    ident["principal_id"], payload.get("division_id")), 200))

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
    async def enforce_rate_limit(request: Request, call_next):
        path = request.url.path
        if path in EXEMPT_PATHS:
            return await call_next(request)

        def too_many(retry_after: int):
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        if path in UNAUTH_LIMITED_PATHS:
            client_ip = request.client.host if request.client else "unknown"
            allowed, retry_after = limiter.check_unauthenticated(client_ip)
            if not allowed:
                return too_many(retry_after)
            return await call_next(request)

        authorization = request.headers.get("authorization") or ""
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            ident = company.identity_for_token(token)
            if ident:
                allowed, retry_after = limiter.check_authenticated(ident["principal_id"])
                if not allowed:
                    return too_many(retry_after)
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
    company.seed_industry_packs()
    import uvicorn
    uvicorn.run(create_app(company), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
