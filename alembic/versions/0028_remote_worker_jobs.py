"""Add remote_worker_jobs for pull-agent lease + mock complete."""
from alembic import op


revision = "0028_remote_worker_jobs"
down_revision = "0027_worker_hosts"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS remote_worker_jobs(
          id TEXT PRIMARY KEY,
          host_id TEXT NOT NULL,
          task_id TEXT NOT NULL,
          worker_run_id TEXT,
          status TEXT NOT NULL,
          lease_owner TEXT,
          lease_expires_at TEXT,
          attempts INTEGER NOT NULL,
          result_json TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          created_by TEXT NOT NULL)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
