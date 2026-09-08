"""Add work_order_replays append-only ledger."""
from alembic import op


revision = "0026_work_order_replays"
down_revision = "0025_durable_finance"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS work_order_replays(
          id TEXT PRIMARY KEY,
          work_order_id TEXT NOT NULL,
          attempt INTEGER NOT NULL,
          workflow_digest TEXT NOT NULL,
          status TEXT NOT NULL,
          outcome_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
