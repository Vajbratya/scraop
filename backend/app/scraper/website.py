from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from .rss import fetch_feed_entries
from .scoring import score_post
from .utils import discover_rss_links, fetch_text


def iter_sitemap_urls(homepage: str, max_urls: int = 500) -> list[str]:
    sitemap_candidates = [
        urljoin(homepage, "/sitemap.xml"),
        urljoin(homepage, "/sitemap_index.xml"),
        urljoin(homepage, "/sitemap-index.xml"),
    ]
    urls: list[str] = []
    for sm in sitemap_candidates:
        xml = fetch_text(sm)
        if not xml:
            continue
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            continue
        for loc in root.iter():
            if loc.tag.endswith("loc") and loc.text:
                u = loc.text.strip()
                if u.startswith("http"):
                    urls.append(u)
                    if len(urls) >= max_urls:
                        return urls
    return urls


def scrape_homepage_sources(homepage: str) -> list[dict[str, Any]]:
    html = fetch_text(homepage)
    entries: list[dict[str, Any]] = []
    if html:
        for feed in discover_rss_links(html, homepage):
            for e in fetch_feed_entries(feed):
                entries.append(e)
    # Fallback: try sitemaps but without full article parsing, keep URLs as posts
    if not entries:
        for u in iter_sitemap_urls(homepage):
            entries.append({"title": None, "url": u, "content": None, "published_at": None})
    return entries


def normalize_entries(company: str, platform: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    norm: list[dict[str, Any]] = []
    for e in entries:
        title = e.get("title")
        content = e.get("content")
        url = e.get("url")
        published_at = e.get("published_at")
        score = score_post(
            published_at=published_at, content_length=(len(content) if content else 0), source_weight=1.2
        )
        norm.append(
            {
                "company": company,
                "platform": platform,
                "url": url,
                "title": title,
                "content": content,
                "published_at": published_at,
                "score": score,
            }
        )
    return norm
