"""Quality inspection records."""
from alembic import op

revision = "0003_quality_control"
down_revision = "0002_hardware_skills"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE IF NOT EXISTS qc_inspections(
          id TEXT PRIMARY KEY, task_id TEXT NOT NULL, artifact_hash TEXT NOT NULL,
          inspector TEXT NOT NULL, verdict TEXT NOT NULL, created_at TEXT NOT NULL)""")


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
