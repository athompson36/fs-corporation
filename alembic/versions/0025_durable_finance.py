"""Add invoices, finance_adjustments, and budget_period_closures."""
from alembic import op


revision = "0025_durable_finance"
down_revision = "0024_company_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS finance_adjustments(
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          kind TEXT NOT NULL,
          billed_cost_id TEXT NOT NULL,
          amount_cents INTEGER NOT NULL,
          reason TEXT NOT NULL,
          invoice_id TEXT)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices(
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          period_start TEXT NOT NULL,
          period_end TEXT NOT NULL,
          total_cents INTEGER NOT NULL,
          line_count INTEGER NOT NULL,
          body TEXT NOT NULL,
          status TEXT NOT NULL)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_period_closures(
          id TEXT PRIMARY KEY,
          budget_period_id TEXT NOT NULL,
          closed_at TEXT NOT NULL,
          closed_by TEXT NOT NULL,
          snapshot TEXT NOT NULL)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
