"""Add approval-gated HR staffing proposals."""
from alembic import op


revision = "0021_staffing_proposals"
down_revision = "0020_career_ladder"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS staffing_proposals(
          id TEXT PRIMARY KEY,
          kind TEXT NOT NULL CHECK(kind IN ('hire','reassign','promote','retire_role')),
          department_id TEXT NOT NULL REFERENCES departments(id),
          position_id TEXT NOT NULL,
          level_id TEXT REFERENCES career_levels(id),
          rationale TEXT NOT NULL,
          evidence TEXT NOT NULL,
          cost_estimate_cents INTEGER NOT NULL,
          proposed_by TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
          approver TEXT,
          decided_at TEXT,
          created_at TEXT NOT NULL)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_pending_staffing_proposal
        ON staffing_proposals(kind, department_id, position_id)
        WHERE status='pending'
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS staffing_scan_cooldown(
          id TEXT PRIMARY KEY CHECK(id='default'),
          last_run TEXT NOT NULL,
          cooldown_until TEXT NOT NULL)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
