"""Add approval-gated divisions and industry packs."""
from alembic import op


revision = "0022_divisions"
down_revision = "0021_staffing_proposals"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS industry_packs(
          id TEXT PRIMARY KEY,
          industry TEXT NOT NULL,
          body TEXT NOT NULL,
          enabled INTEGER NOT NULL)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS divisions(
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          industry_pack_id TEXT NOT NULL REFERENCES industry_packs(id),
          status TEXT NOT NULL CHECK(status IN ('proposed','active','inactive')),
          activated_by TEXT,
          activated_at TEXT,
          proposed_by TEXT NOT NULL,
          created_at TEXT NOT NULL)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS division_departments(
          division_id TEXT NOT NULL REFERENCES divisions(id),
          department_id TEXT NOT NULL REFERENCES departments(id),
          PRIMARY KEY(division_id,department_id))
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS division_activations(
          id TEXT PRIMARY KEY,
          division_id TEXT NOT NULL REFERENCES divisions(id),
          action TEXT NOT NULL,
          actor TEXT NOT NULL,
          at TEXT NOT NULL,
          note TEXT)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
