"""Effective settings resolution: overlay → env → catalog default."""
from __future__ import annotations

import json
import os
from pathlib import Path

from company.settings_catalog import CATALOG, _coerce_bool, validate_value

SECRET_NAMES = (
    "MODEL_PROVIDER_API_KEY",
    "ANTHROPIC_API_KEY",
    "GITHUB_APP_ID",
    "GITHUB_INSTALLATION_ID",
    "GITHUB_PRIVATE_KEY_FILE",
    "GITHUB_WEBHOOK_SECRET",
    "FEED_API_KEY",
    "IMAGE_PROVIDER_API_KEY",
    "VAPID_PUBLIC_KEY",
    "VAPID_PRIVATE_KEY",
    "FS_CORP_TAILSCALE_AUTHKEY",
)


def _meta_public(meta: dict) -> dict:
    out = {
        "key": meta["key"],
        "type": meta["type"],
        "default": meta["default"],
        "editable": meta["editable"],
        "restart_required": meta["restart_required"],
        "description": meta["description"],
    }
    if "min" in meta:
        out["min"] = meta["min"]
    if "max" in meta:
        out["max"] = meta["max"]
    if "enum_values" in meta:
        out["enum_values"] = list(meta["enum_values"])
    return out


def _parse_env(meta: dict, raw: str) -> object:
    kind = meta["type"]
    if kind == "bool":
        return _coerce_bool(raw)
    if kind in ("int", "float"):
        return raw.strip()
    return raw


def effective(company, key: str) -> dict:
    if key not in CATALOG:
        raise ValueError(f"Unknown setting key: {key}")
    meta = CATALOG[key]
    row = company.db.execute(
        "SELECT value_json FROM company_settings WHERE key=?", (key,)
    ).fetchone()
    if row:
        return {
            **_meta_public(meta),
            "value": validate_value(key, json.loads(row["value_json"])),
            "source": "overlay",
        }
    env_name = meta.get("env_name") or key
    raw = os.environ.get(env_name)
    if raw is not None and str(raw).strip() != "":
        return {
            **_meta_public(meta),
            "value": validate_value(key, _parse_env(meta, raw)),
            "source": "env",
        }
    return {
        **_meta_public(meta),
        "value": meta["default"],
        "source": "default",
    }


def list_settings(company) -> list[dict]:
    items = []
    for key in sorted(CATALOG):
        try:
            items.append(effective(company, key))
        except ValueError:
            # One stale overlay or malformed environment value must not hide the catalog.
            meta = CATALOG[key]
            items.append(
                {
                    **_meta_public(meta),
                    "value": meta["default"],
                    "source": "default",
                }
            )
    return items


def _secret_configured(name: str) -> bool:
    raw = os.environ.get(name)
    if raw is not None and str(raw).strip() != "":
        if name.endswith("_FILE") or name.endswith("_PATH"):
            return Path(raw.strip()).expanduser().is_file()
        return True
    # fs-dev often stores VAPID material as *_FILE paths only.
    if name == "VAPID_PUBLIC_KEY":
        path = (os.environ.get("VAPID_PUBLIC_KEY_FILE") or "").strip()
        return bool(path) and Path(path).expanduser().is_file()
    if name == "VAPID_PRIVATE_KEY":
        path = (os.environ.get("VAPID_PRIVATE_KEY_FILE") or "").strip()
        return bool(path) and Path(path).expanduser().is_file()
    return False


def secrets_status() -> list[dict]:
    return [{"name": name, "configured": _secret_configured(name)} for name in SECRET_NAMES]
