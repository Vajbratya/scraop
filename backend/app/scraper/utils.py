from __future__ import annotations

import re
from typing import Iterable

import httpx

USER_AGENT = "Mozilla/5.0 (compatible; scraperbot/1.0; +https://example.com/bot)"


def fetch_text(url: str, timeout: float = 15.0) -> str | None:
    try:
        resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
        if resp.status_code >= 400:
            return None
        return resp.text
    except Exception:
        return None


RSS_LINK_RE = re.compile(r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', re.I)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)


def discover_rss_links(html: str, base_url: str) -> list[str]:
    links: list[str] = []
    for tag in RSS_LINK_RE.findall(html):
        href_match = HREF_RE.search(tag)
        if href_match:
            href = href_match.group(1)
            if href.startswith("http://") or href.startswith("https://"):
                links.append(href)
            elif href.startswith("/"):
                # Resolve simple root-relative
                from urllib.parse import urljoin

                links.append(urljoin(base_url, href))
    # Common conventional feeds
    for path in ("/feed", "/rss", "/atom.xml", "/index.xml", "/blog/rss", "/blog/atom.xml"):
        from urllib.parse import urljoin

        links.append(urljoin(base_url, path))
    # Deduplicate
    seen: set[str] = set()
    uniq: list[str] = []
    for u in links:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq
