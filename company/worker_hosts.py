"""Remote worker host registry and heartbeat status (dispatch stays same-host)."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

from company.core import now


TOKEN_PREFIX = "fs-corporation-worker-host:"
DEFAULT_TTL_SEC = 120


def hash_worker_host_token(token: str) -> str:
    if not token or not isinstance(token, str):
        raise ValueError("Token required")
    return hashlib.sha256((TOKEN_PREFIX + token).encode()).hexdigest()


def heartbeat_ttl_sec(company=None) -> int:
    if company is not None:
        try:
            return int(company.effective_setting("FS_CORP_WORKER_HOST_HEARTBEAT_TTL_SEC"))
        except (ValueError, TypeError):
            pass
    raw = (os.environ.get("FS_CORP_WORKER_HOST_HEARTBEAT_TTL_SEC") or "").strip()
    if raw:
        return max(1, int(raw))
    return DEFAULT_TTL_SEC


def _require_https_base_url(base_url: str) -> str:
    url = (base_url or "").strip().rstrip("/")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        raise ValueError("base_url must be an https origin (no credentials)")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ValueError("base_url must be an https origin without path/query/fragment")
    return f"https://{parts.netloc}"


def _row_public(row) -> dict:
    return {
        "id": row["id"],
        "label": row["label"],
        "base_url": row["base_url"],
        "enabled": bool(row["enabled"]),
        "last_heartbeat_at": row["last_heartbeat_at"],
        "last_heartbeat_meta": json.loads(row["last_heartbeat_meta"] or "null"),
        "created_at": row["created_at"],
        "created_by": row["created_by"],
    }


def _parse_stamp(stamp: str | None):
    if not stamp:
        return None
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def host_state(row, *, ttl_sec: int, now_dt=None) -> str:
    if not row["enabled"]:
        return "disabled"
    last = _parse_stamp(row["last_heartbeat_at"])
    if last is None:
        return "stale"
    current = now_dt or now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    age = (current - last).total_seconds()
    if age <= ttl_sec:
        return "ready"
    return "stale"


def create_worker_host(company, actor: str, *, label: str, base_url: str) -> dict:
    company._ceo(actor)
    name = (label or "").strip()
    if not name:
        raise ValueError("label required")
    origin = _require_https_base_url(base_url)
    host_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    stamp = now().isoformat()
    with company.tx():
        company.db.execute(
            "INSERT INTO worker_hosts VALUES(?,?,?,?,?,?,?,?,?)",
            (
                host_id,
                name,
                origin,
                1,
                hash_worker_host_token(token),
                None,
                None,
                stamp,
                actor,
            ),
        )
        company._event(
            "worker_host.created",
            {"id": host_id, "label": name, "base_url": origin},
            actor_id=actor,
        )
    out = {
        "id": host_id,
        "label": name,
        "base_url": origin,
        "enabled": True,
        "last_heartbeat_at": None,
        "last_heartbeat_meta": None,
        "created_at": stamp,
        "created_by": actor,
        "token": token,
    }
    return out


def list_worker_hosts(company) -> list[dict]:
    rows = company.db.execute(
        "SELECT * FROM worker_hosts ORDER BY created_at, id"
    ).fetchall()
    ttl = heartbeat_ttl_sec(company)
    out = []
    for row in rows:
        item = _row_public(row)
        item["state"] = host_state(row, ttl_sec=ttl)
        out.append(item)
    return out


def set_worker_host_enabled(company, actor: str, host_id: str, enabled: bool) -> dict:
    company._ceo(actor)
    row = company.db.execute(
        "SELECT * FROM worker_hosts WHERE id=?", (host_id,)
    ).fetchone()
    if not row:
        raise ValueError("Worker host not found")
    flag = 1 if enabled else 0
    with company.tx():
        company.db.execute(
            "UPDATE worker_hosts SET enabled=? WHERE id=?", (flag, host_id)
        )
        kind = "worker_host.updated" if enabled else "worker_host.disabled"
        company._event(kind, {"id": host_id, "enabled": bool(flag)}, actor_id=actor)
    row = company.db.execute(
        "SELECT * FROM worker_hosts WHERE id=?", (host_id,)
    ).fetchone()
    item = _row_public(row)
    item["state"] = host_state(row, ttl_sec=heartbeat_ttl_sec(company))
    return item


def delete_worker_host(company, actor: str, host_id: str) -> dict:
    company._ceo(actor)
    row = company.db.execute(
        "SELECT * FROM worker_hosts WHERE id=?", (host_id,)
    ).fetchone()
    if not row:
        raise ValueError("Worker host not found")
    with company.tx():
        company.db.execute("DELETE FROM worker_hosts WHERE id=?", (host_id,))
        company._event("worker_host.updated", {"id": host_id, "deleted": True}, actor_id=actor)
    return {"deleted": True, "id": host_id}


def require_host_token(company, host_id: str, token: str):
    """Validate host heartbeat token; return host row. Fail closed."""
    row = company.db.execute(
        "SELECT * FROM worker_hosts WHERE id=?", (host_id,)
    ).fetchone()
    if not row:
        raise PermissionError("Unknown worker host")
    if hash_worker_host_token(token) != row["heartbeat_token_hash"]:
        raise PermissionError("Invalid worker host token")
    if not row["enabled"]:
        raise PermissionError("Worker host disabled")
    return row


def record_worker_host_heartbeat(
    company, host_id: str, token: str, meta: dict | None = None
) -> dict:
    row = company.db.execute(
        "SELECT * FROM worker_hosts WHERE id=?", (host_id,)
    ).fetchone()
    if not row:
        raise PermissionError("Unknown worker host")
    if hash_worker_host_token(token) != row["heartbeat_token_hash"]:
        raise PermissionError("Invalid worker host token")
    if not row["enabled"]:
        raise PermissionError("Worker host disabled")
    stamp = now().isoformat()
    meta_json = json.dumps(meta) if meta is not None else None
    with company.tx():
        company.db.execute(
            "UPDATE worker_hosts SET last_heartbeat_at=?, last_heartbeat_meta=? WHERE id=?",
            (stamp, meta_json, host_id),
        )
        company._event(
            "worker_host.heartbeat",
            {"id": host_id, "at": stamp},
            actor_id=f"worker-host:{host_id}",
        )
    row = company.db.execute(
        "SELECT * FROM worker_hosts WHERE id=?", (host_id,)
    ).fetchone()
    item = _row_public(row)
    item["state"] = host_state(row, ttl_sec=heartbeat_ttl_sec(company))
    return item


def remote_host_status_rows(company) -> list[dict]:
    ttl = heartbeat_ttl_sec(company)
    rows = company.db.execute(
        "SELECT * FROM worker_hosts ORDER BY label, id"
    ).fetchall()
    out = []
    for row in rows:
        item = {
            "id": row["id"],
            "label": row["label"],
            "base_url": row["base_url"],
            "enabled": bool(row["enabled"]),
            "state": host_state(row, ttl_sec=ttl),
            "last_heartbeat_at": row["last_heartbeat_at"],
        }
        meta = json.loads(row["last_heartbeat_meta"] or "null")
        if meta is not None:
            item["last_heartbeat_meta"] = meta
        out.append(item)
    return out
