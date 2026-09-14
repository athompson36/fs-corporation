"""Work-order baseline/after ops measurements."""
from alembic import op

revision = "0029_work_order_measurements"
down_revision = "0028_remote_worker_jobs"
branch_labels = None
depends_on = None

def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order_measurements(
          id TEXT PRIMARY KEY,
          work_order_id TEXT NOT NULL,
          phase TEXT NOT NULL,
          metrics_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          UNIQUE(work_order_id, phase))
        """
    )

def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
