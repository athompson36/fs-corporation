"""Worker sprite configuration and editable identity fields."""
import json
from pathlib import Path

from alembic import op

revision = "0018_worker_identity"
down_revision = "0017_floorplans"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    columns = {
        row[1]
        for row in conn.exec_driver_sql("PRAGMA table_info(employees)").fetchall()
    }
    for column in ("headline", "viewpoint", "strengths", "growth_focus"):
        if column not in columns:
            op.execute(f"ALTER TABLE employees ADD COLUMN {column} TEXT")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sprite_sets(
          id TEXT PRIMARY KEY, layers TEXT NOT NULL,
          allowed_palettes TEXT NOT NULL, body TEXT NOT NULL)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_sprites(
          employee_id TEXT PRIMARY KEY REFERENCES employees(id),
          sprite_set TEXT NOT NULL REFERENCES sprite_sets(id),
          body TEXT, palette TEXT, accessories TEXT NOT NULL,
          updated_by TEXT NOT NULL, updated_at TEXT NOT NULL)
        """
    )
    path = Path(__file__).resolve().parents[2] / "config" / "sprite-sets.json"
    for sprite_id, sprite_set in json.loads(path.read_text()).items():
        conn.exec_driver_sql(
            """INSERT OR REPLACE INTO sprite_sets(
                 id,layers,allowed_palettes,body) VALUES(?,?,?,?)""",
            (
                sprite_id,
                json.dumps(sprite_set["layers"], sort_keys=True, separators=(",", ":")),
                json.dumps(
                    sprite_set["allowed_palettes"],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                json.dumps(sprite_set["body"], sort_keys=True, separators=(",", ":")),
            ),
        )


def downgrade():
    raise NotImplementedError("Forward-only migrations; restore from backup instead")
