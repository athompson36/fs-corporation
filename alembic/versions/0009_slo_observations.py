"""Sourced SLO observations. Definitions stay unmeasured until recorded."""
from alembic import op

revision = "0009_slo_observations"
down_revision = "0008_push_notifications"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """CREATE TABLE IF NOT EXISTS slo_observations(
              id TEXT PRIMARY KEY, slo_id TEXT NOT NULL, value REAL NOT NULL, source TEXT NOT NULL,
              window_start TEXT NOT NULL, window_end TEXT NOT NULL, recorded_at TEXT NOT NULL,
              recorded_by TEXT NOT NULL)"""
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
