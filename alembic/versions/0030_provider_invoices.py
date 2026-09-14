"""Provider invoices and allocations."""
from alembic import op

revision = "0030_provider_invoices"
down_revision = "0029_work_order_measurements"
branch_labels = None
depends_on = None

def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_invoices(
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          provider TEXT NOT NULL,
          external_id TEXT NOT NULL,
          total_cents INTEGER NOT NULL,
          issued_at TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL,
          UNIQUE(provider, external_id))
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_invoice_allocations(
          id TEXT PRIMARY KEY,
          provider_invoice_id TEXT NOT NULL,
          billed_cost_id TEXT NOT NULL,
          allocated_cents INTEGER NOT NULL,
          created_at TEXT NOT NULL,
          created_by TEXT NOT NULL,
          UNIQUE(provider_invoice_id, billed_cost_id))
        """
    )

def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
