"""Owner inbox and project dispatch briefs for the mobile CEO companion."""
from alembic import op

revision = "0006_mobile_companion"
down_revision = "0005_worker_runs"
branch_labels = None
depends_on = None

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS owner_requests(
          id TEXT PRIMARY KEY, project_id TEXT, department_id TEXT NOT NULL,
          requester TEXT NOT NULL, kind TEXT NOT NULL, subject TEXT NOT NULL,
          body TEXT NOT NULL, status TEXT NOT NULL, owner_response TEXT,
          created_at TEXT NOT NULL, responded_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS project_dispatches(
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, department_id TEXT NOT NULL,
          work_order_id TEXT NOT NULL, brief TEXT NOT NULL,
          acceptance_criteria TEXT NOT NULL, budget_cents INTEGER NOT NULL,
          due_at TEXT, created_at TEXT NOT NULL)""",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
