"""Isolated worker run audit trail."""
from alembic import op

revision = "0005_worker_runs"
down_revision = "0004_employee_development"
branch_labels = None
depends_on = None

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS worker_runs(
          id TEXT PRIMARY KEY, worker_id TEXT NOT NULL, task_id TEXT NOT NULL,
          runtime TEXT NOT NULL, scratch_root TEXT NOT NULL, status TEXT NOT NULL,
          started_at TEXT NOT NULL, finished_at TEXT)""",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
