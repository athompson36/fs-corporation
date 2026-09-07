"""Persisted headquarters floorplans, rooms, and department requirements."""
import json
from pathlib import Path

from alembic import op

revision = "0017_floorplans"
down_revision = "0016_department_editing"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS floorplans(
          id TEXT PRIMARY KEY, division_id TEXT, name TEXT NOT NULL,
          grid_cols INTEGER NOT NULL, grid_rows INTEGER NOT NULL, status TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS floorplan_rooms(
          id TEXT PRIMARY KEY,
          floorplan_id TEXT NOT NULL REFERENCES floorplans(id),
          department_id TEXT REFERENCES departments(id),
          room_type TEXT NOT NULL, label TEXT NOT NULL,
          grid_x INTEGER NOT NULL, grid_y INTEGER NOT NULL,
          width INTEGER NOT NULL, height INTEGER NOT NULL,
          capacity INTEGER NOT NULL, status TEXT NOT NULL,
          source_expansion_id TEXT REFERENCES expansions(id),
          created_by TEXT NOT NULL, created_at TEXT NOT NULL)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS room_requirements(
          department_id TEXT NOT NULL REFERENCES departments(id),
          required_room_type TEXT NOT NULL, min_capacity INTEGER NOT NULL,
          PRIMARY KEY(department_id, required_room_type))
        """
    )
    config_path = Path(__file__).resolve().parents[2] / "config" / "room-requirements.json"
    requirements = json.loads(config_path.read_text())
    conn = op.get_bind()
    for department_id, requirement in requirements.items():
        conn.exec_driver_sql(
            """
            INSERT OR REPLACE INTO room_requirements(
              department_id, required_room_type, min_capacity)
            SELECT ?,?,? WHERE EXISTS(
              SELECT 1 FROM departments WHERE id=?)
            """,
            (
                department_id,
                requirement["required_room_type"],
                requirement["min_capacity"],
                department_id,
            ),
        )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
