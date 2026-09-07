"""Parse Tailscale Funnel/status JSON for the GitHub webhook public URL."""
from __future__ import annotations
import json
import os
import shutil
import subprocess

WEBHOOK_PATH = "/api/v1/github/webhooks"


def funnel_opt_in() -> bool:
    return (os.environ.get("FS_CORP_TAILSCALE_FUNNEL_WEBHOOKS") or "").strip() == "1"


def public_url_from_env() -> str | None:
    value = (os.environ.get("FS_CORP_GITHUB_WEBHOOK_PUBLIC_URL") or "").strip()
    return value or None


def parse_funnel_public_url(funnel_status: dict | None, self_dns_name: str | None = None) -> str | None:
    """Extract https://{host}/api/v1/github/webhooks from Tailscale Funnel serve JSON.

    Only returns a URL when Funnel status includes an active handler for the webhook path.
    Opt-in alone must not advertise a public URL (github.com would get connection failures).
    """
    data = funnel_status or {}
    web = data.get("Web") or data.get("web") or {}
    if isinstance(web, dict):
        for host_key, cfg in web.items():
            host = str(host_key).split(":")[0]
            if not host:
                continue
            handlers = {}
            if isinstance(cfg, dict):
                handlers = cfg.get("Handlers") or cfg.get("handlers") or {}
            if not isinstance(handlers, dict):
                continue
            for path in handlers:
                if str(path) == WEBHOOK_PATH or str(path).startswith(WEBHOOK_PATH + "/"):
                    return f"https://{host.rstrip('.')}{WEBHOOK_PATH}"
    return None


def probe_funnel_webhooks() -> dict:
    """Return status for github/status. Never raises; fail-closed."""
    env_url = public_url_from_env()
    result = {
        "opt_in": funnel_opt_in(),
        "path": WEBHOOK_PATH,
        "public_url": env_url,
        "cli": "live_unavailable",
    }
    exe = shutil.which("tailscale")
    if not exe:
        return result
    result["cli"] = "advertised"
    funnel_data = None
    dns_name = None
    try:
        out = subprocess.run(
            [exe, "funnel", "status", "--json"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        if out.returncode == 0 and (out.stdout or "").strip():
            funnel_data = json.loads(out.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        funnel_data = None
    try:
        out = subprocess.run(
            [exe, "status", "--json"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        if out.returncode == 0 and (out.stdout or "").strip():
            st = json.loads(out.stdout)
            dns_name = ((st.get("Self") or {}).get("DNSName") or "").rstrip(".")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        dns_name = None
    parsed = parse_funnel_public_url(funnel_data, dns_name)
    if parsed:
        result["public_url"] = parsed
    elif env_url:
        result["public_url"] = env_url
    return result
