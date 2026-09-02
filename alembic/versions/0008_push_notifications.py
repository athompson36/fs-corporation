"""Owner push subscriptions and fail-closed delivery records."""
from alembic import op

revision = "0008_push_notifications"
down_revision = "0007_feed_polls"
branch_labels = None
depends_on = None

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS push_subscriptions(
          id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, endpoint TEXT NOT NULL,
          keys TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS push_deliveries(
          id TEXT PRIMARY KEY, subscription_id TEXT NOT NULL, kind TEXT NOT NULL,
          subject TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)""",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
