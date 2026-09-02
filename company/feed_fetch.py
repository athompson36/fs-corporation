"""Fetch and parse HTTPS RSS/Atom feeds for market intelligence."""
from __future__ import annotations
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx

ATOM = "{http://www.w3.org/2005/Atom}"


def _headers() -> dict[str, str]:
    headers = {"User-Agent": "FS-Corporation/feed-pilot", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"}
    key = (os.environ.get("FEED_API_KEY") or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_date(value: str | None, *, fallback: str) -> str:
    if not value:
        return fallback
    value = value.strip()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _iso(parsed)
    except ValueError:
        pass
    try:
        return _iso(parsedate_to_datetime(value))
    except (TypeError, ValueError):
        return fallback


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    if node.text and node.text.strip():
        return node.text.strip()
    return "".join(node.itertext()).strip()


def _link(entry: ET.Element, atom: bool) -> str:
    if atom:
        for child in entry.findall(f"{ATOM}link"):
            href = child.attrib.get("href")
            if href and child.attrib.get("rel", "alternate") in {"alternate", ""}:
                return href
        link = entry.find(f"{ATOM}link")
        return link.attrib.get("href", "") if link is not None else ""
    link = entry.find("link")
    if link is not None and link.text:
        return link.text.strip()
    guid = entry.find("guid")
    return _text(guid) if guid is not None else ""


def parse_feed(xml_bytes: bytes, *, observed_at: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    tag = root.tag.rsplit("}", 1)[-1].lower()
    items: list[dict] = []
    if tag == "feed":
        for entry in root.findall(f"{ATOM}entry")[:50]:
            title = _text(entry.find(f"{ATOM}title"))
            source = _link(entry, atom=True)
            if not title or not source.startswith("https://"):
                continue
            published = entry.find(f"{ATOM}published")
            if published is None:
                published = entry.find(f"{ATOM}updated")
            summary_elem = entry.find(f"{ATOM}summary")
            if summary_elem is None:
                summary_elem = entry.find(f"{ATOM}content")
            summary = _text(summary_elem)
            summary = re.sub(r"\s+", " ", summary)[:2000]
            items.append({
                "source": source,
                "title": title,
                "published_at": _parse_date(_text(published), fallback=observed_at),
                "observed_at": observed_at,
                "summary": summary or title,
            })
        return items
    if tag == "rss":
        channel = root.find("channel")
        if channel is None:
            return items
        for entry in channel.findall("item")[:50]:
            title = _text(entry.find("title"))
            source = _link(entry, atom=False)
            if not title or not source.startswith("https://"):
                continue
            pub = entry.find("pubDate")
            if pub is None:
                pub = entry.find("published")
            desc = entry.find("description")
            if desc is None:
                desc = entry.find("summary")
            summary = _text(desc)
            summary = re.sub(r"\s+", " ", summary)[:2000]
            items.append({
                "source": source,
                "title": title,
                "published_at": _parse_date(_text(pub), fallback=observed_at),
                "observed_at": observed_at,
                "summary": summary or title,
            })
    return items


def fetch_feed(url: str, *, observed_at: str) -> list[dict]:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url, headers=_headers())
        response.raise_for_status()
    content_type = (response.headers.get("content-type") or "").lower()
    if "html" in content_type and b"<rss" not in response.content[:4096] and b"<feed" not in response.content[:4096]:
        raise ValueError("Feed URL returned HTML, not RSS/Atom")
    return parse_feed(response.content, observed_at=observed_at)
