"""Initial company schema."""
from alembic import op
from company.schema import SCHEMA

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    statements = [part.strip() for part in SCHEMA.split(";") if part.strip()]
    for statement in statements:
        op.execute(statement)


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
