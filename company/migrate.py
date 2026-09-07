"""Bring a file-backed company database to the Alembic head at startup.

`apply_schema` uses `CREATE TABLE IF NOT EXISTS`, which cannot add columns. A database
created by an older application build can therefore miss column-only revisions such as
`0011_pairing_access_level`. Running `alembic upgrade head` after schema apply closes that
gap. Ephemeral `:memory:` databases skip Alembic — the in-repo SCHEMA is the authority there.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from pathlib import Path

HEAD_REVISION = "0014_org_hierarchy"
ROOT = Path(__file__).resolve().parents[1]

_locks_guard = threading.Lock()
_path_locks: dict[str, threading.Lock] = {}


def is_ephemeral_path(path: str) -> bool:
    value = (path or "").strip()
    return value == ":memory:" or value.startswith("file:")


def _path_lock(absolute: str) -> threading.Lock:
    with _locks_guard:
        lock = _path_locks.get(absolute)
        if lock is None:
            lock = threading.Lock()
            _path_locks[absolute] = lock
        return lock


def _current_revision(absolute: str) -> str | None:
    try:
        conn = sqlite3.connect(absolute, timeout=30.0)
    except sqlite3.Error:
        return None
    try:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def ensure_migrations(db_path: str) -> str:
    """Upgrade *db_path* to head and return the resulting revision id.

    Raises RuntimeError if the database is still behind head after upgrade.
    Concurrent callers for the same path are serialized so SQLite does not deadlock.
    """
    if is_ephemeral_path(db_path):
        return HEAD_REVISION

    absolute = str(Path(db_path).resolve())
    with _path_lock(absolute):
        current = _current_revision(absolute)
        if current == HEAD_REVISION:
            return current

        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config(str(ROOT / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{absolute}")
        os.environ["FS_CORP_ALEMBIC_QUIET"] = "1"
        logging.getLogger("alembic").setLevel(logging.WARNING)
        logging.getLogger("alembic.runtime.migration").setLevel(logging.WARNING)
        command.upgrade(cfg, "head")

        script = ScriptDirectory.from_config(cfg)
        head = script.get_current_head()
        current = _current_revision(absolute)
        if current != head:
            raise RuntimeError(
                f"Database schema drift: alembic_version={current!r} head={head!r}. "
                f"Run `alembic upgrade head` against {absolute} before starting the service."
            )
        if head != HEAD_REVISION:
            raise RuntimeError(
                f"company.migrate.HEAD_REVISION={HEAD_REVISION!r} is stale; alembic head is {head!r}. "
                "Update HEAD_REVISION when adding a migration."
            )
        return current or head
