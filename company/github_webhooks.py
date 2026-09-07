"""GitHub webhook signature verification and normalization. Payload is untrusted task data."""
from __future__ import annotations
import hashlib
import hmac
import json
import os

ALLOWED_EVENTS = frozenset({"ping", "push", "pull_request"})
MAX_BODY_BYTES = 1024 * 1024


class WebhookError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def webhook_secret() -> str | None:
    value = (os.environ.get("GITHUB_WEBHOOK_SECRET") or "").strip()
    return value or None


def webhook_secret_configured() -> bool:
    return webhook_secret() is not None


def verify_signature(secret: str, body: bytes, signature_header: str | None) -> None:
    if not signature_header or not signature_header.startswith("sha256="):
        raise WebhookError(401, "Missing or invalid X-Hub-Signature-256")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    if not hmac.compare_digest(expected, received):
        raise WebhookError(401, "Invalid webhook signature")


def normalize_event(event: str, payload: dict) -> dict:
    """Extract a small trusted-shape summary. Never treat payload as authority."""
    repo = payload.get("repository") or {}
    repo_id = str(repo.get("id") or "") or None
    action = payload.get("action")
    summary_parts = [event]
    if action:
        summary_parts.append(str(action))
    if event == "pull_request":
        number = payload.get("number")
        if number is not None:
            summary_parts.append(f"#{number}")
        head = ((payload.get("pull_request") or {}).get("head") or {}).get("sha")
        if head:
            summary_parts.append(str(head)[:12])
    elif event == "push":
        ref = payload.get("ref")
        if ref:
            summary_parts.append(str(ref))
        after = payload.get("after")
        if after:
            summary_parts.append(str(after)[:12])
    elif event == "ping":
        zen = payload.get("zen")
        if zen:
            summary_parts.append(str(zen)[:80])
    return {
        "event": event,
        "repo_id": repo_id,
        "repo_full_name": repo.get("full_name"),
        "action": action,
        "summary": " ".join(summary_parts),
    }


def parse_and_verify(
    *,
    body: bytes,
    event: str | None,
    delivery_id: str | None,
    signature_header: str | None,
) -> tuple[str, str, dict]:
    secret = webhook_secret()
    if not secret:
        raise WebhookError(503, "GitHub webhook secret is not configured")
    if len(body) > MAX_BODY_BYTES:
        raise WebhookError(413, "Webhook body too large")
    if not event:
        raise WebhookError(422, "Missing X-GitHub-Event")
    if not delivery_id:
        raise WebhookError(422, "Missing X-GitHub-Delivery")
    verify_signature(secret, body, signature_header)
    if event not in ALLOWED_EVENTS:
        return event, delivery_id, {"_ignored": True}
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebhookError(422, "Invalid JSON body") from exc
    if not isinstance(payload, dict):
        raise WebhookError(422, "Webhook JSON must be an object")
    return event, delivery_id, payload
