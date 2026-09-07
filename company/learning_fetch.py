"""Allowlisted HTTPS documentation fetch for skill study (task data only)."""
from __future__ import annotations
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

_DEFAULT_FILE = Path(__file__).resolve().parents[1] / "config" / "learning-sources.example.json"


def learning_sources_path() -> Path | None:
    override = (os.environ.get("FS_CORP_LEARNING_SOURCES_FILE") or "").strip()
    if override:
        path = Path(override)
        return path if path.is_file() else None
    if _DEFAULT_FILE.is_file():
        return _DEFAULT_FILE
    return None


def load_url_prefixes(path: Path | None = None) -> list[str]:
    resolved = path or learning_sources_path()
    if resolved is None:
        raise NotImplementedError(
            "Live documentation fetch requires an approved source list; "
            "set FS_CORP_LEARNING_SOURCES_FILE or ship config/learning-sources.example.json; "
            "see docs/20-hardware-skills.md"
        )
    data = json.loads(resolved.read_text())
    prefixes = [str(p).strip() for p in (data.get("url_prefixes") or []) if str(p).strip()]
    if not prefixes:
        raise NotImplementedError("Learning sources file has no url_prefixes")
    for prefix in prefixes:
        parsed = urlparse(prefix)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"Learning source prefix must be HTTPS: {prefix!r}")
    return prefixes


def url_allowed(url: str, prefixes: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    return any(url.startswith(prefix) for prefix in prefixes)


def _title_and_summary(text: str, content_type: str) -> tuple[str, str]:
    title = ""
    body = text
    if "html" in (content_type or "").lower() or "<html" in text[:500].lower():
        match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.I | re.S)
        if match:
            title = re.sub(r"\s+", " ", match.group(1)).strip()
        body = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
        body = re.sub(r"<style[^>]*>.*?</style>", " ", body, flags=re.I | re.S)
        body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    summary = body[:500]
    if not title:
        title = (summary[:80] + "…") if len(summary) > 80 else (summary or "untitled")
    return title, summary


def fetch_learning_document(url: str, *, prefixes: list[str] | None = None) -> dict:
    """GET an allowlisted HTTPS URL; return metadata for study ingest."""
    allowed = prefixes if prefixes is not None else load_url_prefixes()
    if not url_allowed(url, allowed):
        raise PermissionError("URL is not on the approved learning source allowlist")
    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        response = client.get(
            url,
            headers={"User-Agent": "FS-Corporation/learning-pilot", "Accept": "text/html,text/plain,*/*"},
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        text = response.text
    title, summary = _title_and_summary(text, content_type)
    return {
        "url": url,
        "title": title,
        "summary": summary,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "status_code": response.status_code,
    }
