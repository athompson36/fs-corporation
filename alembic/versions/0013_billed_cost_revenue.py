"""Billed cost and revenue tables (integer minor units)."""
from alembic import op

revision = "0013_billed_cost_revenue"
down_revision = "0012_github_webhook_deliveries"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS billed_costs(
          id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, amount_cents INTEGER NOT NULL,
          usage_tokens INTEGER NOT NULL, provider TEXT NOT NULL, profile_id TEXT NOT NULL,
          source TEXT NOT NULL, task_id TEXT)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS revenue(
          id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, amount_cents INTEGER NOT NULL,
          source TEXT NOT NULL, note TEXT NOT NULL DEFAULT '')
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
