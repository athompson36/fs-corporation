"""Shared SQLite DDL for the reference core and Alembic. No network access."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS policies(version INTEGER PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, base INTEGER NOT NULL,
  body TEXT NOT NULL, author TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
  version INTEGER NOT NULL, expires TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, actor TEXT NOT NULL,
  project TEXT NOT NULL, action TEXT NOT NULL, cost INTEGER NOT NULL, version INTEGER NOT NULL,
  status TEXT NOT NULL, artifact_hash TEXT);
CREATE TABLE IF NOT EXISTS ledger(task_id TEXT PRIMARY KEY REFERENCES tasks(id),
  actor TEXT NOT NULL, cost INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS completions(project TEXT PRIMARY KEY, task_id TEXT NOT NULL UNIQUE,
  reviewer TEXT NOT NULL, artifact_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS signals(id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL,
  body TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS expansions(id TEXT PRIMARY KEY, source_project TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL, contractor TEXT);
CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL,
  event_id TEXT, schema_version INTEGER NOT NULL DEFAULT 1, actor_id TEXT, policy_version INTEGER,
  correlation_id TEXT, project_id TEXT);
CREATE TABLE IF NOT EXISTS consultant_proposals(
  id TEXT PRIMARY KEY, body TEXT NOT NULL, author TEXT NOT NULL,
  status TEXT NOT NULL, approver TEXT, reason TEXT,
  source_hash TEXT, revision_of TEXT);
CREATE TABLE IF NOT EXISTS identities(
  principal_id TEXT PRIMARY KEY, kind TEXT NOT NULL, token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL, scopes TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS departments(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, head_title TEXT NOT NULL, mission TEXT NOT NULL,
  measures TEXT NOT NULL, room_type TEXT NOT NULL, initially_active INTEGER NOT NULL,
  default_model_profile TEXT NOT NULL, body TEXT NOT NULL,
  origin TEXT NOT NULL DEFAULT 'seed', status TEXT NOT NULL DEFAULT 'active',
  display_order INTEGER NOT NULL DEFAULT 0, parent_department_id TEXT,
  updated_at TEXT, updated_by TEXT);
CREATE TABLE IF NOT EXISTS positions(
  id TEXT PRIMARY KEY, department_id TEXT NOT NULL REFERENCES departments(id), title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active', display_order INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT);
CREATE TABLE IF NOT EXISTS department_revisions(
  id TEXT PRIMARY KEY, department_id TEXT NOT NULL, version INTEGER NOT NULL,
  body TEXT NOT NULL, changed_by TEXT NOT NULL, changed_at TEXT NOT NULL, reason TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects(
  id TEXT PRIMARY KEY, brief TEXT NOT NULL, classification TEXT NOT NULL,
  github_upstream_id TEXT, github_fork_id TEXT, allowed_branches TEXT NOT NULL,
  enrolled_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS delegations(
  id TEXT PRIMARY KEY, grantor TEXT NOT NULL, grantee TEXT NOT NULL, parent_id TEXT,
  actions TEXT NOT NULL, projects TEXT NOT NULL, budget_cents INTEGER NOT NULL,
  per_action_cents INTEGER NOT NULL, expires_at TEXT NOT NULL, requires_approval TEXT NOT NULL,
  approval_rights TEXT NOT NULL, can_redelegate INTEGER NOT NULL, status TEXT NOT NULL,
  created_at TEXT NOT NULL, FOREIGN KEY(parent_id) REFERENCES delegations(id));
CREATE TABLE IF NOT EXISTS model_profiles(
  id TEXT PRIMARY KEY, body TEXT NOT NULL, enabled INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS model_assignments(
  id TEXT PRIMARY KEY, scope_kind TEXT NOT NULL, scope_id TEXT NOT NULL,
  profile_id TEXT NOT NULL, version INTEGER NOT NULL, effective_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_orders(
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL, policy_version INTEGER NOT NULL,
  workflow_digest TEXT NOT NULL, max_cost_cents INTEGER NOT NULL, payload TEXT NOT NULL,
  status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS queue(
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL UNIQUE, actor TEXT NOT NULL, project TEXT NOT NULL,
  action TEXT NOT NULL, cost INTEGER NOT NULL, payload TEXT NOT NULL,
  lease_owner TEXT, lease_until TEXT, attempts INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbox(
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
  status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reservations(
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL UNIQUE, actor TEXT NOT NULL,
  amount_cents INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS artifacts(
  id TEXT PRIMARY KEY, hash TEXT NOT NULL UNIQUE, storage_uri TEXT NOT NULL,
  producer TEXT NOT NULL, task_id TEXT NOT NULL, project TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS github_enrollments(
  project_id TEXT PRIMARY KEY, upstream_repo_id TEXT NOT NULL, fork_repo_id TEXT NOT NULL,
  protected_branches TEXT NOT NULL, branch_prefix TEXT NOT NULL, permitted_actions TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS github_effects(
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, task_id TEXT NOT NULL, operation TEXT NOT NULL,
  repo_id TEXT NOT NULL, branch TEXT NOT NULL, status TEXT NOT NULL, remote_id TEXT);
CREATE TABLE IF NOT EXISTS impact_briefs(
  id TEXT PRIMARY KEY, signal_id TEXT NOT NULL UNIQUE, project_id TEXT,
  body TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS budget_periods(
  id TEXT PRIMARY KEY, scope TEXT NOT NULL, period_start TEXT NOT NULL,
  period_end TEXT NOT NULL, limit_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS memories(
  id TEXT PRIMARY KEY, project_id TEXT, department_id TEXT, classification TEXT NOT NULL,
  body TEXT NOT NULL, approved INTEGER NOT NULL, author TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS command_idempotency(
  key TEXT PRIMARY KEY, principal_id TEXT NOT NULL, request_hash TEXT NOT NULL,
  status_code INTEGER NOT NULL, response_body TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS benchmark_results(
  id TEXT PRIMARY KEY, role TEXT NOT NULL, profile_id TEXT NOT NULL,
  quality REAL, latency_ms INTEGER, cost_cents INTEGER, failure_rate REAL,
  recorded_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS consultant_reviews(
  id TEXT PRIMARY KEY, trigger_kind TEXT NOT NULL, last_run TEXT NOT NULL, cooldown_until TEXT);
CREATE TABLE IF NOT EXISTS skills(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, platform TEXT NOT NULL, department_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS acquired_skills(
  skill_id TEXT NOT NULL, holder TEXT NOT NULL, source_hash TEXT, acquired_at TEXT NOT NULL,
  PRIMARY KEY(skill_id, holder));
CREATE TABLE IF NOT EXISTS project_capabilities(
  project_id TEXT PRIMARY KEY, domain TEXT NOT NULL, platform TEXT, required_skills TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS learning_assignments(
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, skill_id TEXT NOT NULL, learner TEXT NOT NULL,
  department_id TEXT NOT NULL, signal_id TEXT, status TEXT NOT NULL, source TEXT,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS qc_inspections(
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL, artifact_hash TEXT NOT NULL,
  inspector TEXT NOT NULL, verdict TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS employees(
  id TEXT PRIMARY KEY, position_id TEXT NOT NULL, display_name TEXT NOT NULL,
  attributes TEXT NOT NULL, background TEXT NOT NULL, hired_at TEXT NOT NULL, status TEXT NOT NULL,
  headline TEXT, viewpoint TEXT, strengths TEXT, growth_focus TEXT);
CREATE TABLE IF NOT EXISTS training_records(
  id TEXT PRIMARY KEY, employee_id TEXT NOT NULL, assignment_id TEXT NOT NULL,
  skill_id TEXT NOT NULL, source TEXT, summary TEXT, studied_at TEXT, certified_at TEXT,
  certifier TEXT, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS performance_goals(
  id TEXT PRIMARY KEY, employee_id TEXT NOT NULL, title TEXT NOT NULL,
  target INTEGER NOT NULL, period TEXT NOT NULL, set_by TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS performance_reviews(
  id TEXT PRIMARY KEY, employee_id TEXT NOT NULL, reviewer TEXT NOT NULL,
  score INTEGER NOT NULL, notes TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS worker_runs(
  id TEXT PRIMARY KEY, worker_id TEXT NOT NULL, task_id TEXT NOT NULL,
  runtime TEXT NOT NULL, scratch_root TEXT NOT NULL, status TEXT NOT NULL,
  started_at TEXT NOT NULL, finished_at TEXT);
CREATE TABLE IF NOT EXISTS owner_requests(
  id TEXT PRIMARY KEY, project_id TEXT, department_id TEXT NOT NULL,
  requester TEXT NOT NULL, kind TEXT NOT NULL, subject TEXT NOT NULL,
  body TEXT NOT NULL, status TEXT NOT NULL, owner_response TEXT,
  created_at TEXT NOT NULL, responded_at TEXT);
CREATE TABLE IF NOT EXISTS project_dispatches(
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, department_id TEXT NOT NULL,
  work_order_id TEXT NOT NULL, brief TEXT NOT NULL,
  acceptance_criteria TEXT NOT NULL, budget_cents INTEGER NOT NULL,
  due_at TEXT, created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued_for_head',
  head_principal_id TEXT, head_inbox_at TEXT);
CREATE TABLE IF NOT EXISTS feed_sources(
  id TEXT PRIMARY KEY, url TEXT NOT NULL, approved_by TEXT NOT NULL,
  approved_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feed_polls(
  id TEXT PRIMARY KEY, source_id TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS push_subscriptions(
  id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, endpoint TEXT NOT NULL,
  keys TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS push_deliveries(
  id TEXT PRIMARY KEY, subscription_id TEXT NOT NULL, kind TEXT NOT NULL,
  subject TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS slo_observations(
  id TEXT PRIMARY KEY, slo_id TEXT NOT NULL, value REAL NOT NULL, source TEXT NOT NULL,
  window_start TEXT NOT NULL, window_end TEXT NOT NULL, recorded_at TEXT NOT NULL, recorded_by TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pairing_tickets(
  id TEXT PRIMARY KEY, ticket_hash TEXT NOT NULL, created_by TEXT NOT NULL,
  created_at TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL,
  redeemed_at TEXT, companion_principal TEXT, access_level TEXT NOT NULL DEFAULT 'admin');
CREATE TABLE IF NOT EXISTS github_webhook_deliveries(
  delivery_id TEXT PRIMARY KEY, event TEXT NOT NULL, repo_id TEXT,
  summary TEXT NOT NULL, received_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS billed_costs(
  id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, amount_cents INTEGER NOT NULL,
  usage_tokens INTEGER NOT NULL, provider TEXT NOT NULL, profile_id TEXT NOT NULL,
  source TEXT NOT NULL, task_id TEXT);
CREATE TABLE IF NOT EXISTS revenue(
  id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, amount_cents INTEGER NOT NULL,
  source TEXT NOT NULL, note TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS department_seats(
  id TEXT PRIMARY KEY, department_id TEXT NOT NULL UNIQUE REFERENCES departments(id),
  principal_id TEXT, title TEXT NOT NULL,
  status TEXT NOT NULL, appointed_by TEXT, appointed_at TEXT, vacated_at TEXT);
CREATE TABLE IF NOT EXISTS position_assignments(
  id TEXT PRIMARY KEY, position_id TEXT NOT NULL REFERENCES positions(id),
  department_id TEXT NOT NULL REFERENCES departments(id), principal_id TEXT NOT NULL,
  status TEXT NOT NULL, reports_to_seat_id TEXT REFERENCES department_seats(id),
  assigned_by TEXT NOT NULL, assigned_at TEXT NOT NULL, released_at TEXT);
CREATE TABLE IF NOT EXISTS project_department_activations(
  project_id TEXT NOT NULL REFERENCES projects(id),
  department_id TEXT NOT NULL REFERENCES departments(id),
  activated_by TEXT NOT NULL, activated_at TEXT NOT NULL,
  PRIMARY KEY(project_id, department_id));
CREATE TABLE IF NOT EXISTS dispatch_assignments(
  id TEXT PRIMARY KEY, dispatch_id TEXT NOT NULL REFERENCES project_dispatches(id),
  assignee TEXT NOT NULL, assigned_by TEXT NOT NULL, assigned_at TEXT NOT NULL,
  queue_task_id TEXT, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cross_department_requests(
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  requesting_department_id TEXT NOT NULL REFERENCES departments(id),
  delivering_department_id TEXT NOT NULL REFERENCES departments(id),
  budget_owner TEXT NOT NULL, due_at TEXT NOT NULL,
  acceptance_criteria TEXT NOT NULL, escalation_path TEXT NOT NULL,
  budget_cents INTEGER NOT NULL, status TEXT NOT NULL,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL,
  accepted_by TEXT, accepted_at TEXT,
  subject TEXT NOT NULL, brief TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS floorplans(
  id TEXT PRIMARY KEY, division_id TEXT, name TEXT NOT NULL,
  grid_cols INTEGER NOT NULL, grid_rows INTEGER NOT NULL, status TEXT NOT NULL,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS floorplan_rooms(
  id TEXT PRIMARY KEY, floorplan_id TEXT NOT NULL REFERENCES floorplans(id),
  department_id TEXT REFERENCES departments(id), room_type TEXT NOT NULL,
  label TEXT NOT NULL, grid_x INTEGER NOT NULL, grid_y INTEGER NOT NULL,
  width INTEGER NOT NULL, height INTEGER NOT NULL, capacity INTEGER NOT NULL,
  status TEXT NOT NULL, source_expansion_id TEXT REFERENCES expansions(id),
  created_by TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS room_requirements(
  department_id TEXT NOT NULL REFERENCES departments(id),
  required_room_type TEXT NOT NULL, min_capacity INTEGER NOT NULL,
  PRIMARY KEY(department_id, required_room_type));
CREATE TABLE IF NOT EXISTS sprite_sets(
  id TEXT PRIMARY KEY, layers TEXT NOT NULL,
  allowed_palettes TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS worker_sprites(
  employee_id TEXT PRIMARY KEY REFERENCES employees(id),
  sprite_set TEXT NOT NULL REFERENCES sprite_sets(id),
  body TEXT, palette TEXT, accessories TEXT NOT NULL,
  updated_by TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS activity_sessions(
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN (
    'work','review','meeting','cross_department','context_request')),
  project_id TEXT, department_id TEXT, room_id TEXT REFERENCES floorplan_rooms(id),
  participants TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('open','closed')),
  started_event_id INTEGER NOT NULL UNIQUE REFERENCES events(seq),
  ended_event_id INTEGER REFERENCES events(seq),
  started_at TEXT NOT NULL, ended_at TEXT);
CREATE TABLE IF NOT EXISTS career_levels(
  id TEXT PRIMARY KEY, division_id TEXT, department_id TEXT,
  level_index INTEGER NOT NULL, title TEXT NOT NULL,
  required_skills TEXT NOT NULL, min_accepted_artifacts INTEGER NOT NULL,
  min_review_score INTEGER NOT NULL, quality_standard TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uq_career_level_scope_index
  ON career_levels(
    COALESCE(division_id, ''), COALESCE(department_id, ''), level_index);
CREATE TABLE IF NOT EXISTS employee_levels(
  employee_id TEXT PRIMARY KEY REFERENCES employees(id),
  level_id TEXT NOT NULL REFERENCES career_levels(id),
  effective_at TEXT NOT NULL, set_by TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS promotion_records(
  id TEXT PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(id),
  from_level TEXT NOT NULL REFERENCES career_levels(id),
  to_level TEXT NOT NULL REFERENCES career_levels(id),
  evidence TEXT NOT NULL, proposed_by TEXT NOT NULL, approved_by TEXT,
  status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
  created_at TEXT NOT NULL, decided_at TEXT);
CREATE TABLE IF NOT EXISTS staffing_proposals(
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN ('hire','reassign','promote','retire_role')),
  department_id TEXT NOT NULL REFERENCES departments(id),
  position_id TEXT NOT NULL, level_id TEXT REFERENCES career_levels(id),
  rationale TEXT NOT NULL, evidence TEXT NOT NULL,
  cost_estimate_cents INTEGER NOT NULL, proposed_by TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
  approver TEXT, decided_at TEXT, created_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pending_staffing_proposal
  ON staffing_proposals(kind, department_id, position_id)
  WHERE status='pending';
CREATE TABLE IF NOT EXISTS staffing_scan_cooldown(
  id TEXT PRIMARY KEY CHECK(id='default'),
  last_run TEXT NOT NULL, cooldown_until TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS industry_packs(
  id TEXT PRIMARY KEY, industry TEXT NOT NULL, body TEXT NOT NULL,
  enabled INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS divisions(
  id TEXT PRIMARY KEY, name TEXT NOT NULL,
  industry_pack_id TEXT NOT NULL REFERENCES industry_packs(id),
  status TEXT NOT NULL CHECK(status IN ('proposed','active','inactive')),
  activated_by TEXT, activated_at TEXT, proposed_by TEXT NOT NULL,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS division_departments(
  division_id TEXT NOT NULL REFERENCES divisions(id),
  department_id TEXT NOT NULL REFERENCES departments(id),
  PRIMARY KEY(division_id,department_id));
CREATE TABLE IF NOT EXISTS division_activations(
  id TEXT PRIMARY KEY, division_id TEXT NOT NULL REFERENCES divisions(id),
  action TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL, note TEXT);
"""

SLO_DEFINITIONS = (
    {"id": "api.health_availability", "name": "Control API health availability", "unit": "ratio"},
    {"id": "api.request_latency_ms", "name": "Control API request latency", "unit": "milliseconds"},
    {"id": "worker.dispatch_success", "name": "Isolated worker dispatch success", "unit": "ratio"},
    {"id": "queue.blocked_count", "name": "Blocked or denied dispatch count", "unit": "count"},
)

GRANT_REQUIRED = {"actions", "projects", "budget_cents", "per_action_cents", "expires_at", "requires_approval"}
GRANT_OPTIONAL = {"approval_rights", "departments"}
POLICY_REQUIRED = {"version", "company_budget_cents", "grants"}
MAX_DELEGATION_DEPTH = 2
KNOWN_ACTIONS = {"draft", "review", "prepare_pr", "provision_room", "inspect_room"}
COMPANION_SCOPES = (
    "company.read", "company.pause", "company.resume",
    "policy.approve", "consultant.decide", "consultant.read",
    "project.enroll", "audit.read", "organization.read", "organization.write",
    "owner.escalate",
)
PAIRING_READ_ONLY_SCOPES = (
    "company.read", "audit.read", "consultant.read", "organization.read",
)
PAIRING_USER_SCOPES = PAIRING_READ_ONLY_SCOPES + ("owner.escalate",)
PAIRING_LEVELS = (
    {"id": "read_only", "label": "Read only", "scopes": PAIRING_READ_ONLY_SCOPES,
     "summary": "Dashboard and lists only. No approve, pause, enroll, or respond."},
    {"id": "user", "label": "User", "scopes": PAIRING_USER_SCOPES,
     "summary": "Read access plus owner-inbox escalations. No CEO actions."},
    {"id": "admin", "label": "Admin / CEO mobile", "scopes": COMPANION_SCOPES,
     "summary": "Full companion: approve, pause, enroll, dispatch, inbox respond."},
)
PAIRING_LEVEL_IDS = {level["id"] for level in PAIRING_LEVELS}


def pairing_level(level_id):
    for level in PAIRING_LEVELS:
        if level["id"] == level_id:
            return level
    raise ValueError("Unknown pairing access level")


def pairing_levels_catalog():
    return [{"id": l["id"], "label": l["label"], "scopes": list(l["scopes"]), "summary": l["summary"]}
            for l in PAIRING_LEVELS]


def apply_schema(db):
    db.executescript(SCHEMA)
