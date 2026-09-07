"""Allowlisted company settings catalog (non-secret runtime knobs + read-only host-bound)."""
from __future__ import annotations

import math
from typing import Any, TypedDict
from urllib.parse import urlsplit


class SettingDef(TypedDict, total=False):
    key: str
    type: str
    default: Any
    editable: bool
    restart_required: bool
    description: str
    min: int | float
    max: int | float
    enum_values: tuple[str, ...]
    env_name: str


CATALOG: dict[str, SettingDef] = {
    "FS_CORP_RATE_LIMIT_AUTH": {
        "key": "FS_CORP_RATE_LIMIT_AUTH",
        "type": "int",
        "default": 120,
        "min": 1,
        "editable": True,
        "restart_required": True,
        "description": "Authenticated requests per rate-limit window",
    },
    "FS_CORP_RATE_LIMIT_UNAUTH": {
        "key": "FS_CORP_RATE_LIMIT_UNAUTH",
        "type": "int",
        "default": 60,
        "min": 1,
        "editable": True,
        "restart_required": True,
        "description": "Unauthenticated requests per rate-limit window",
    },
    "FS_CORP_RATE_LIMIT_WINDOW_SEC": {
        "key": "FS_CORP_RATE_LIMIT_WINDOW_SEC",
        "type": "float",
        "default": 60.0,
        "editable": True,
        "restart_required": True,
        "description": "Rate-limit sliding window length in seconds",
    },
    "FS_CORP_SSE_IDLE_SEC": {
        "key": "FS_CORP_SSE_IDLE_SEC",
        "type": "float",
        "default": 1.0,
        "min": 0,
        "editable": True,
        "restart_required": False,
        "description": "SSE idle sleep seconds between event pages",
    },
    "FS_CORP_PUBLIC_URL": {
        "key": "FS_CORP_PUBLIC_URL",
        "type": "string",
        "default": "",
        "editable": True,
        "restart_required": False,
        "description": "Public URL for companion pairing and callbacks",
    },
    "FS_CORP_DEFAULT_WORKER_RUNTIME": {
        "key": "FS_CORP_DEFAULT_WORKER_RUNTIME",
        "type": "enum",
        "default": "subprocess",
        "enum_values": ("subprocess", "container"),
        "editable": True,
        "restart_required": False,
        "description": "Default isolated worker runtime for new dispatches",
    },
    "FS_CORP_MODEL_CENTS_PER_1K_TOKENS": {
        "key": "FS_CORP_MODEL_CENTS_PER_1K_TOKENS",
        "type": "int",
        "default": 0,
        "min": 0,
        "editable": True,
        "restart_required": False,
        "description": "Simulated model price in USD cents per 1k tokens",
    },
    "CHATDEV_ALLOW_CONTROL_PLANE": {
        "key": "CHATDEV_ALLOW_CONTROL_PLANE",
        "type": "bool",
        "default": False,
        "editable": True,
        "restart_required": False,
        "description": "Allow ChatDev runs to invoke control-plane actions",
    },
    "FS_CORP_IDEMPOTENCY_RETENTION_DAYS": {
        "key": "FS_CORP_IDEMPOTENCY_RETENTION_DAYS",
        "type": "int",
        "default": 7,
        "min": 1,
        "editable": True,
        "restart_required": False,
        "description": "Days to retain command idempotency records before prune",
    },
    "FS_CORP_LAN_IP": {
        "key": "FS_CORP_LAN_IP",
        "type": "string",
        "default": "",
        "editable": False,
        "restart_required": False,
        "description": "LAN edge IP (host-bound; read-only in Settings)",
    },
    "FS_CORP_WORKER_NIC_IP": {
        "key": "FS_CORP_WORKER_NIC_IP",
        "type": "string",
        "default": "",
        "editable": False,
        "restart_required": False,
        "description": "Worker NIC IP (host-bound; read-only in Settings)",
    },
    "FS_CORP_GATEWAY_EGRESS": {
        "key": "FS_CORP_GATEWAY_EGRESS",
        "type": "string",
        "default": "",
        "editable": False,
        "restart_required": False,
        "description": "Gateway egress address (host-bound; read-only in Settings)",
    },
}

EDITABLE_KEYS = frozenset(k for k, d in CATALOG.items() if d["editable"])
READONLY_KEYS = frozenset(k for k, d in CATALOG.items() if not d["editable"])


def _coerce_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    raise ValueError("invalid bool")


def _coerce_int(raw: Any) -> int:
    if isinstance(raw, bool):
        raise ValueError("invalid int")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        if raw != int(raw):
            raise ValueError("invalid int")
        return int(raw)
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            raise ValueError("invalid int")
        numeric = stripped[1:] if stripped.startswith(("+", "-")) else stripped
        if not numeric.isdigit():
            raise ValueError("invalid int")
        return int(stripped)
    raise ValueError("invalid int")


def _coerce_float(raw: Any) -> float:
    if isinstance(raw, bool):
        raise ValueError("invalid float")
    if isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            raise ValueError("invalid float")
        try:
            value = float(stripped)
        except ValueError as exc:
            raise ValueError("invalid float") from exc
    else:
        raise ValueError("invalid float")
    if not math.isfinite(value):
        raise ValueError("invalid float")
    return value


def validate_value(key: str, raw: Any) -> Any:
    if key not in CATALOG:
        raise ValueError(f"Unknown setting key: {key}")
    meta = CATALOG[key]
    kind = meta["type"]
    if kind == "int":
        value = _coerce_int(raw)
        minimum = meta.get("min")
        if minimum is not None and value < minimum:
            raise ValueError("below minimum")
        maximum = meta.get("max")
        if maximum is not None and value > maximum:
            raise ValueError("above maximum")
        return value
    if kind == "float":
        value = _coerce_float(raw)
        if meta["key"] == "FS_CORP_RATE_LIMIT_WINDOW_SEC" and value <= 0:
            raise ValueError("must be positive")
        minimum = meta.get("min")
        if minimum is not None and value < minimum:
            raise ValueError("below minimum")
        return value
    if kind == "string":
        if not isinstance(raw, str):
            raise ValueError("invalid string")
        if key == "FS_CORP_PUBLIC_URL" and raw:
            try:
                parsed = urlsplit(raw)
                host = parsed.hostname
            except ValueError as exc:
                raise ValueError("invalid public URL") from exc
            if (
                parsed.scheme != "https"
                or not host
                or parsed.username is not None
                or parsed.password is not None
                or parsed.fragment
            ):
                raise ValueError(
                    "public URL must use https with a host, no userinfo, and no fragment"
                )
        return raw
    if kind == "bool":
        return _coerce_bool(raw)
    if kind == "enum":
        value = str(raw)
        allowed = meta.get("enum_values") or ()
        if value not in allowed:
            raise ValueError("invalid enum value")
        return value
    raise ValueError(f"Unsupported type: {kind}")
