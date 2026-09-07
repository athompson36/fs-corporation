"""Idempotency key retention (default 7 days) and prune helper."""
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone

DEFAULT_RETENTION_DAYS = 7


def retention_days_from_env() -> int:
    raw = (os.environ.get("FS_CORP_IDEMPOTENCY_RETENTION_DAYS") or "").strip()
    if not raw:
        return DEFAULT_RETENTION_DAYS
    days = int(raw)
    if days < 1:
        raise ValueError("FS_CORP_IDEMPOTENCY_RETENTION_DAYS must be >= 1")
    return days


def cutoff_iso(*, older_than_days: int, now_dt: datetime | None = None) -> str:
    if older_than_days < 1:
        raise ValueError("older_than_days must be >= 1")
    current = now_dt or datetime.now(timezone.utc)
    return (current - timedelta(days=older_than_days)).isoformat()


def prune_command_idempotency(db, *, older_than_days: int, now_dt: datetime | None = None) -> int:
    """Delete command_idempotency rows with created_at strictly before the cutoff.

    Returns the number of deleted rows.
    """
    cutoff = cutoff_iso(older_than_days=older_than_days, now_dt=now_dt)
    cur = db.execute(
        "DELETE FROM command_idempotency WHERE created_at < ?",
        (cutoff,),
    )
    return int(cur.rowcount or 0)
