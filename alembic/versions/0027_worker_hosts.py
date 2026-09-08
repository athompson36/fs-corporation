"""Add worker_hosts registry for remote host heartbeat status (no remote dispatch)."""
from alembic import op


revision = "0027_worker_hosts"
down_revision = "0026_work_order_replays"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_hosts(
          id TEXT PRIMARY KEY,
          label TEXT NOT NULL,
          base_url TEXT NOT NULL,
          enabled INTEGER NOT NULL,
          heartbeat_token_hash TEXT NOT NULL,
          last_heartbeat_at TEXT,
          last_heartbeat_meta TEXT,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
