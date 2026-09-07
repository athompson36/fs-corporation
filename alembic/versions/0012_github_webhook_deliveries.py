"""GitHub webhook delivery records."""
from alembic import op

revision = "0012_github_webhook_deliveries"
down_revision = "0011_pairing_access_level"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS github_webhook_deliveries(
          delivery_id TEXT PRIMARY KEY, event TEXT NOT NULL, repo_id TEXT,
          summary TEXT NOT NULL, received_at TEXT NOT NULL, status TEXT NOT NULL)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
