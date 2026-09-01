"""Employee records, training files, and performance reviews."""
from alembic import op

revision = "0004_employee_development"
down_revision = "0003_quality_control"
branch_labels = None
depends_on = None

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS employees(
          id TEXT PRIMARY KEY, position_id TEXT NOT NULL, display_name TEXT NOT NULL,
          attributes TEXT NOT NULL, background TEXT NOT NULL, hired_at TEXT NOT NULL, status TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS training_records(
          id TEXT PRIMARY KEY, employee_id TEXT NOT NULL, assignment_id TEXT NOT NULL,
          skill_id TEXT NOT NULL, source TEXT, summary TEXT, studied_at TEXT, certified_at TEXT,
          certifier TEXT, status TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS performance_goals(
          id TEXT PRIMARY KEY, employee_id TEXT NOT NULL, title TEXT NOT NULL,
          target INTEGER NOT NULL, period TEXT NOT NULL, set_by TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS performance_reviews(
          id TEXT PRIMARY KEY, employee_id TEXT NOT NULL, reviewer TEXT NOT NULL,
          score INTEGER NOT NULL, notes TEXT NOT NULL, created_at TEXT NOT NULL)""",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
