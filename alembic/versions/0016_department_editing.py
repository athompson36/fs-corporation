"""Runtime department/position editing columns and revision history."""
from alembic import op

revision = "0016_department_editing"
down_revision = "0015_cross_dept_work_orders"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dept_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(departments)").fetchall()}
    if "origin" not in dept_cols:
        op.execute("ALTER TABLE departments ADD COLUMN origin TEXT NOT NULL DEFAULT 'seed'")
    if "status" not in dept_cols:
        op.execute("ALTER TABLE departments ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if "display_order" not in dept_cols:
        op.execute("ALTER TABLE departments ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0")
    if "parent_department_id" not in dept_cols:
        op.execute("ALTER TABLE departments ADD COLUMN parent_department_id TEXT")
    if "updated_at" not in dept_cols:
        op.execute("ALTER TABLE departments ADD COLUMN updated_at TEXT")
    if "updated_by" not in dept_cols:
        op.execute("ALTER TABLE departments ADD COLUMN updated_by TEXT")

    pos_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(positions)").fetchall()}
    if "status" not in pos_cols:
        op.execute("ALTER TABLE positions ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if "display_order" not in pos_cols:
        op.execute("ALTER TABLE positions ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0")
    if "updated_at" not in pos_cols:
        op.execute("ALTER TABLE positions ADD COLUMN updated_at TEXT")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS department_revisions(
          id TEXT PRIMARY KEY, department_id TEXT NOT NULL, version INTEGER NOT NULL,
          body TEXT NOT NULL, changed_by TEXT NOT NULL, changed_at TEXT NOT NULL,
          reason TEXT NOT NULL)
        """
    )
    # Align status with initially_active for legacy rows still on default 'active'
    op.execute(
        """
        UPDATE departments SET status='dormant'
        WHERE initially_active=0 AND status='active' AND origin='seed'
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
