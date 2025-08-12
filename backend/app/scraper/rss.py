from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

from .utils import fetch_text


def parse_rfc2822(date_str: str) -> datetime | None:
    from email.utils import parsedate_to_datetime

    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def parse_w3c(date_str: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def fetch_feed_entries(feed_url: str, max_items: int = 100) -> list[dict[str, Any]]:
    xml_text = fetch_text(feed_url)
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    items: list[dict[str, Any]] = []
    if root.tag.endswith("rss") or root.find("channel") is not None:
        # RSS 2.0
        channel = root.find("channel") or root
        for item in channel.findall("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")
            title = title_el.text.strip() if title_el is not None and title_el.text else None
            link = link_el.text.strip() if link_el is not None and link_el.text else None
            description = desc_el.text.strip() if desc_el is not None and desc_el.text else None
            published_at = parse_rfc2822(pub_el.text.strip()) if pub_el is not None and pub_el.text else None
            if link:
                items.append(
                    {
                        "title": title,
                        "url": link,
                        "content": description,
                        "published_at": published_at,
                    }
                )
            if len(items) >= max_items:
                break
    else:
        # Atom
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            content_el = entry.find("atom:content", ns)
            updated_el = entry.find("atom:updated", ns) or entry.find("atom:published", ns)
            link = link_el.attrib.get("href") if link_el is not None else None
            title = title_el.text.strip() if title_el is not None and title_el.text else None
            content = content_el.text.strip() if content_el is not None and content_el.text else None
            published_at = parse_w3c(updated_el.text.strip()) if updated_el is not None and updated_el.text else None
            if link:
                items.append(
                    {
                        "title": title,
                        "url": link,
                        "content": content,
                        "published_at": published_at,
                    }
                )
            if len(items) >= max_items:
                break
    return items
