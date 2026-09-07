"""Add company_settings overlay table for allowlisted runtime knobs."""
from alembic import op


revision = "0024_company_settings"
down_revision = "0023_ceo_scorecard"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_settings(
          key TEXT PRIMARY KEY,
          value_json TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          updated_by TEXT NOT NULL)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
