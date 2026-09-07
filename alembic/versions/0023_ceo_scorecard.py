"""Add CEO objectives and persisted scorecard snapshots."""
from alembic import op


revision = "0023_ceo_scorecard"
down_revision = "0022_divisions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS objectives(
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          division_id TEXT REFERENCES divisions(id),
          due_at TEXT NOT NULL,
          target TEXT NOT NULL,
          created_by TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('open','closed')),
          created_at TEXT NOT NULL,
          closed_at TEXT)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS scorecard_snapshots(
          id TEXT PRIMARY KEY,
          period_start TEXT,
          period_end TEXT,
          metrics TEXT NOT NULL,
          created_at TEXT NOT NULL)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
