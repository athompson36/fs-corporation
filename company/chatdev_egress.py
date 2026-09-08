"""Allowlisted HTTPS destinations for optional ChatDev worker egress."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

_EXAMPLE = Path(__file__).resolve().parents[1] / "config" / "chatdev-egress-allowlist.example.json"


def allowlist_path() -> Path | None:
    override = (os.environ.get("FS_CORP_CHATDEV_EGRESS_ALLOWLIST_FILE") or "").strip()
    if override:
        path = Path(override)
        return path if path.is_file() else None
    return None


def load_https_hosts(path: Path | None = None) -> list[str]:
    resolved = path if path is not None else allowlist_path()
    if resolved is None:
        raise NotImplementedError(
            "ChatDev worker egress allowlist file not configured; "
            "set FS_CORP_CHATDEV_EGRESS_ALLOWLIST_FILE to a JSON file with https_hosts"
        )
    data = json.loads(resolved.read_text())
    hosts = []
    for raw in data.get("https_hosts") or []:
        host = str(raw).strip().lower().rstrip(".")
        if not host or "/" in host or "://" in host or host.startswith("."):
            raise ValueError(f"Allowlist entry must be a hostname only: {raw!r}")
        hosts.append(host)
    if not hosts:
        raise NotImplementedError("ChatDev egress allowlist has no https_hosts")
    return hosts


def url_allowed(url: str, hosts: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    host = parsed.hostname
    if not host:
        return False
    host = host.lower().rstrip(".")
    allowed = {h.lower().rstrip(".") for h in hosts}
    if host in allowed:
        return True
    return any(host.endswith("." + h) for h in allowed)


def egress_mode(company=None) -> str:
    if company is not None:
        try:
            return str(company.effective_setting("FS_CORP_CHATDEV_WORKER_EGRESS") or "none")
        except Exception:
            pass
    raw = (os.environ.get("FS_CORP_CHATDEV_WORKER_EGRESS") or "none").strip().lower()
    return raw if raw in {"none", "allowlist"} else "none"


def docker_network_name() -> str | None:
    name = (os.environ.get("FS_CORP_CHATDEV_EGRESS_DOCKER_NETWORK") or "").strip()
    return name or None


def allowlist_status(company=None) -> dict:
    mode = egress_mode(company)
    configured = False
    count = 0
    path = allowlist_path()
    error = None
    if path is not None:
        try:
            hosts = load_https_hosts(path)
            configured = True
            count = len(hosts)
        except Exception as exc:
            error = str(exc)
    network = docker_network_name()
    ready = mode == "allowlist" and configured and count > 0 and bool(network)
    out = {
        "worker_egress_mode": mode,
        "allowlist_configured": configured,
        "allowlist_count": count,
        "worker_egress_ready": ready,
        "docker_network_configured": bool(network),
    }
    if error:
        out["allowlist_error"] = error
    return out


FORBIDDEN_NETWORKS = frozenset({"", "bridge", "host"})


def claim_egress_policy(company=None) -> dict:
    """Claim payload egress policy; never includes host lists."""
    mode = egress_mode(company)
    if mode != "allowlist":
        return {"mode": "none", "docker_network": None}
    network = (docker_network_name() or "").strip()
    if not network or network.lower() in FORBIDDEN_NETWORKS:
        return {"mode": "none", "docker_network": None}
    return {"mode": "allowlist", "docker_network": network}


def container_network_args(company=None) -> list[str]:
    """Docker --network args. Never returns unrestricted bridge; default none."""
    status = allowlist_status(company)
    if status["worker_egress_ready"]:
        network = docker_network_name()
        assert network  # ready implies configured
        return ["--network", network]
    return ["--network", "none"]
