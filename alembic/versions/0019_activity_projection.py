"""Persist event-derived activity sessions for Corporate HQ."""
from alembic import op


revision = "0019_activity_projection"
down_revision = "0018_worker_identity"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_sessions(
          id TEXT PRIMARY KEY,
          kind TEXT NOT NULL CHECK(kind IN (
            'work','review','meeting','cross_department','context_request')),
          project_id TEXT,
          department_id TEXT,
          room_id TEXT REFERENCES floorplan_rooms(id),
          participants TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('open','closed')),
          started_event_id INTEGER NOT NULL UNIQUE REFERENCES events(seq),
          ended_event_id INTEGER REFERENCES events(seq),
          started_at TEXT NOT NULL,
          ended_at TEXT)
        """
    )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
