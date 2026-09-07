"""Persist cross-department requests separately from execution work orders."""
from alembic import op

revision = "0015_cross_dept_work_orders"
down_revision = "0014_org_hierarchy"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cross_department_requests(
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
          requesting_department_id TEXT NOT NULL,
          delivering_department_id TEXT NOT NULL,
          budget_owner TEXT NOT NULL, due_at TEXT NOT NULL,
          acceptance_criteria TEXT NOT NULL, escalation_path TEXT NOT NULL,
          budget_cents INTEGER NOT NULL, status TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          accepted_by TEXT, accepted_at TEXT,
          subject TEXT NOT NULL, brief TEXT NOT NULL)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
