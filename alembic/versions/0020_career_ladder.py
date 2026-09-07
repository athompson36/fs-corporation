"""Add career ladders and governed promotion records."""
from alembic import op


revision = "0020_career_ladder"
down_revision = "0019_activity_projection"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS career_levels(
          id TEXT PRIMARY KEY,
          division_id TEXT,
          department_id TEXT,
          level_index INTEGER NOT NULL,
          title TEXT NOT NULL,
          required_skills TEXT NOT NULL,
          min_accepted_artifacts INTEGER NOT NULL,
          min_review_score INTEGER NOT NULL,
          quality_standard TEXT NOT NULL)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_levels(
          employee_id TEXT PRIMARY KEY REFERENCES employees(id),
          level_id TEXT NOT NULL REFERENCES career_levels(id),
          effective_at TEXT NOT NULL,
          set_by TEXT NOT NULL)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS promotion_records(
          id TEXT PRIMARY KEY,
          employee_id TEXT NOT NULL REFERENCES employees(id),
          from_level TEXT NOT NULL REFERENCES career_levels(id),
          to_level TEXT NOT NULL REFERENCES career_levels(id),
          evidence TEXT NOT NULL,
          proposed_by TEXT NOT NULL,
          approved_by TEXT,
          status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
          created_at TEXT NOT NULL,
          decided_at TEXT)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_career_level_scope_index
        ON career_levels(
          COALESCE(division_id, ''),
          COALESCE(department_id, ''),
          level_index)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
