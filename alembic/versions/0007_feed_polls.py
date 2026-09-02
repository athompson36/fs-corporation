"""Approved market feed sources and fail-closed poll records."""
from alembic import op

revision = "0007_feed_polls"
down_revision = "0006_mobile_companion"
branch_labels = None
depends_on = None

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS feed_sources(
          id TEXT PRIMARY KEY, url TEXT NOT NULL, approved_by TEXT NOT NULL,
          approved_at TEXT NOT NULL, status TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS feed_polls(
          id TEXT PRIMARY KEY, source_id TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)""",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
