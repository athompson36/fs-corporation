"""Web Push (VAPID) delivery. Keys stay in env, never in SQLite or prompts."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path


def _read_key(name: str, file_var: str) -> str:
    path = (os.environ.get(file_var) or "").strip()
    if path and Path(path).expanduser().is_file():
        return Path(path).expanduser().read_text().strip()
    return (os.environ.get(name) or "").strip()


def vapid_configured() -> bool:
    return bool(_read_key("VAPID_PRIVATE_KEY", "VAPID_PRIVATE_KEY_FILE"))


def vapid_public_key() -> str | None:
    value = _read_key("VAPID_PUBLIC_KEY", "VAPID_PUBLIC_KEY_FILE")
    return value or None


def vapid_contact() -> str:
    return (os.environ.get("VAPID_CONTACT_EMAIL") or "mailto:owner@example.com").strip()


def application_server_key() -> str | None:
    """URL-safe base64 public key for browser PushManager.subscribe."""
    pem = vapid_public_key()
    if not pem:
        return None
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        key = load_pem_public_key(pem.encode())
        numbers = key.public_numbers()
        x = numbers.x.to_bytes(32, "big")
        y = numbers.y.to_bytes(32, "big")
        raw = b"\x04" + x + y
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")
    except Exception:
        return None


def status_summary() -> dict:
    if not vapid_configured():
        return {"configured": False, "live": False}
    public = vapid_public_key()
    out = {"configured": True, "live": True, "contact": vapid_contact()}
    if public:
        out["public_key"] = public
    app_key = application_server_key()
    if app_key:
        out["application_server_key"] = app_key
    return out


def send_push(subscription: dict, payload: dict) -> dict:
    if not vapid_configured():
        raise NotImplementedError("Live web push requires VAPID keys; see docs/24-mobile-companion.md")
    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys") or {}
    if not endpoint or not str(endpoint).startswith("https://"):
        raise ValueError("Push subscription needs an HTTPS endpoint")
    from pywebpush import WebPushException, webpush

    private_key = _read_key("VAPID_PRIVATE_KEY", "VAPID_PRIVATE_KEY_FILE")
    body = json.dumps({"subject": payload.get("subject") or payload.get("title"), **payload})
    try:
        response = webpush(
            subscription_info={"endpoint": endpoint, "keys": keys},
            data=body,
            vapid_private_key=private_key,
            vapid_claims={"sub": vapid_contact()},
        )
    except WebPushException as exc:
        raise RuntimeError(str(exc)) from exc
    status_code = getattr(response, "status_code", None) if response is not None else 201
    return {"status": "applied", "http_status": status_code}
