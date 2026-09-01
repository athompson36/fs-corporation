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
  default_model_profile TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS positions(
  id TEXT PRIMARY KEY, department_id TEXT NOT NULL REFERENCES departments(id), title TEXT NOT NULL);
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
  attributes TEXT NOT NULL, background TEXT NOT NULL, hired_at TEXT NOT NULL, status TEXT NOT NULL);
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
"""

GRANT_REQUIRED = {"actions", "projects", "budget_cents", "per_action_cents", "expires_at", "requires_approval"}
GRANT_OPTIONAL = {"approval_rights"}
POLICY_REQUIRED = {"version", "company_budget_cents", "grants"}
MAX_DELEGATION_DEPTH = 2
KNOWN_ACTIONS = {"draft", "review", "prepare_pr", "provision_room", "inspect_room"}


def apply_schema(db):
    db.executescript(SCHEMA)
