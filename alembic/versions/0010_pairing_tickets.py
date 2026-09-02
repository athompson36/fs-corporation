"""One-time companion pairing tickets."""
from alembic import op

revision = "0010_pairing_tickets"
down_revision = "0009_slo_observations"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """CREATE TABLE IF NOT EXISTS pairing_tickets(
              id TEXT PRIMARY KEY, ticket_hash TEXT NOT NULL, created_by TEXT NOT NULL,
              created_at TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL,
              redeemed_at TEXT, companion_principal TEXT, access_level TEXT NOT NULL DEFAULT 'admin')"""
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
