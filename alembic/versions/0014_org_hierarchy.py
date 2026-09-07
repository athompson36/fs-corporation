"""Org seats, assignments, project department activation, dispatch handoff columns."""
from alembic import op

revision = "0014_org_hierarchy"
down_revision = "0013_billed_cost_revenue"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS department_seats(
          id TEXT PRIMARY KEY, department_id TEXT NOT NULL UNIQUE,
          principal_id TEXT, title TEXT NOT NULL,
          status TEXT NOT NULL, appointed_by TEXT, appointed_at TEXT, vacated_at TEXT)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS position_assignments(
          id TEXT PRIMARY KEY, position_id TEXT NOT NULL,
          department_id TEXT NOT NULL, principal_id TEXT NOT NULL,
          status TEXT NOT NULL, reports_to_seat_id TEXT,
          assigned_by TEXT NOT NULL, assigned_at TEXT NOT NULL, released_at TEXT)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_department_activations(
          project_id TEXT NOT NULL, department_id TEXT NOT NULL,
          activated_by TEXT NOT NULL, activated_at TEXT NOT NULL,
          PRIMARY KEY(project_id, department_id))
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS dispatch_assignments(
          id TEXT PRIMARY KEY, dispatch_id TEXT NOT NULL,
          assignee TEXT NOT NULL, assigned_by TEXT NOT NULL, assigned_at TEXT NOT NULL,
          queue_task_id TEXT, status TEXT NOT NULL)
        """
    )
    conn = op.get_bind()
    cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(project_dispatches)").fetchall()]
    if "status" not in cols:
        op.execute(
            "ALTER TABLE project_dispatches ADD COLUMN status TEXT NOT NULL DEFAULT 'queued_for_head'"
        )
    if "head_principal_id" not in cols:
        op.execute("ALTER TABLE project_dispatches ADD COLUMN head_principal_id TEXT")
    if "head_inbox_at" not in cols:
        op.execute("ALTER TABLE project_dispatches ADD COLUMN head_inbox_at TEXT")


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
