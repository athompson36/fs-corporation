"""Hardware skill catalog tables."""
from alembic import op

revision = "0002_hardware_skills"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS skills(
          id TEXT PRIMARY KEY, name TEXT NOT NULL, platform TEXT NOT NULL, department_id TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS acquired_skills(
          skill_id TEXT NOT NULL, holder TEXT NOT NULL, source_hash TEXT, acquired_at TEXT NOT NULL,
          PRIMARY KEY(skill_id, holder))""",
    """CREATE TABLE IF NOT EXISTS project_capabilities(
          project_id TEXT PRIMARY KEY, domain TEXT NOT NULL, platform TEXT, required_skills TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS learning_assignments(
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, skill_id TEXT NOT NULL, learner TEXT NOT NULL,
          department_id TEXT NOT NULL, signal_id TEXT, status TEXT NOT NULL, source TEXT,
          created_at TEXT NOT NULL)""",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
