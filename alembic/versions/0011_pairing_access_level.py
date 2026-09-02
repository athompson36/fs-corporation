"""Pairing ticket access level."""
from alembic import op

revision = "0011_pairing_access_level"
down_revision = "0010_pairing_tickets"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(pairing_tickets)").fetchall()]
    if "access_level" not in cols:
        op.execute("ALTER TABLE pairing_tickets ADD COLUMN access_level TEXT NOT NULL DEFAULT 'admin'")


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
