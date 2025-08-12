from __future__ import annotations

from collections import deque
from typing import Any
from urllib.parse import urljoin, urlparse
import re

from bs4 import BeautifulSoup  # type: ignore
from sqlmodel import Session, select

from app.models import ScrapedPost, ScrapeJob, CrawlPage
from .website import normalize_entries, scrape_homepage_sources
from app.core.config import settings

DEFAULT_SOURCES: dict[str, dict[str, Any]] = {
    # You can expand or override these via API or config later
    "laudos.ai": {"homepage": "https://laudos.ai/"},
    "laudos": {"homepage": "https://home.laudos.ai/"},
    "laudite": {"homepage": "https://laudite.com.br/"},
    "leorad": {"homepage": "https://leorad.com/"},  # placeholder
}


def upsert_post(session: Session, data: dict[str, Any]) -> bool:
    existing = session.exec(select(ScrapedPost).where(ScrapedPost.url == data["url"])).first()
    if existing:
        changed = False
        fields = ["title", "content", "published_at", "score"]
        for f in fields:
            v = data.get(f)
            if v is not None and getattr(existing, f) != v:
                setattr(existing, f, v)
                changed = True
        if changed:
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return True
        return False
    obj = ScrapedPost(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return True


def run_scraping_for_company(*, session: Session, company: str) -> dict[str, Any]:
    cfg = DEFAULT_SOURCES.get(company) or DEFAULT_SOURCES.get(company.lower())
    if not cfg:
        return {"inserted": 0, "updated": 0, "message": "No configured sources for company"}
    homepage = cfg.get("homepage")
    if not homepage:
        return {"inserted": 0, "updated": 0, "message": "No homepage configured"}

    raw_entries = scrape_homepage_sources(homepage)
    entries = normalize_entries(company=company, platform="website", entries=raw_entries)

    inserted = 0
    for e in entries:
        changed = upsert_post(session, e)
        if changed:
            inserted += 1
    return {"inserted": inserted, "source": homepage}


# Firecrawl-like BFS crawler
HREF_RE = re.compile(r"^https?://", re.I)


def _allowed(url: str, allowed_domains: list[str]) -> bool:
    if not allowed_domains:
        return True
    host = urlparse(url).hostname or ""
    return any(host.endswith(dom) for dom in allowed_domains)


def _match_any(url: str, patterns: list[str]) -> bool:
    for p in patterns:
        try:
            if re.search(p, url):
                return True
        except re.error:
            continue
    return False


def bfs_crawl(*,
    session: Session,
    job: ScrapeJob,
) -> dict[str, Any]:
    visited: set[str] = set()
    q: deque[tuple[str, int]] = deque()
    for seed in job.seeds:
        q.append((seed, 0))
    pages = 0
    created = 0

    while q and pages < job.max_pages:
        url, depth = q.popleft()
        if url in visited:
            continue
        visited.add(url)
        if depth > job.max_depth:
            continue
        if not _allowed(url, job.allowed_domains):
            continue
        # Fetch
        try:
            import httpx

            headers = {"User-Agent": "crawler/1.0"}
            if settings.RENDER_SERVICE_URL and job.render_js:
                # Proxy through a prerender service
                prerender_url = str(settings.RENDER_SERVICE_URL).rstrip("/") + "/render/" + url
                r = httpx.get(prerender_url, headers=headers, timeout=30, follow_redirects=True)
            else:
                r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
            status_code = r.status_code
            html = r.text if status_code < 400 else ""
        except Exception:
            status_code = 0
            html = ""
        # Parse title/text
        title = None
        text = None
        if html:
            try:
                soup = BeautifulSoup(html, "html.parser")
                title = (soup.title.string or "").strip() if soup.title else None
                text = soup.get_text(" ", strip=True)
                # Enqueue links
                for a in soup.find_all("a", href=True):
                    href = a.get("href")
                    if not href:
                        continue
                    full = href if HREF_RE.search(href) else urljoin(url, href)
                    if not _allowed(full, job.allowed_domains):
                        continue
                    if job.include_patterns and not _match_any(full, job.include_patterns):
                        continue
                    if job.exclude_patterns and _match_any(full, job.exclude_patterns):
                        continue
                    if full not in visited:
                        q.append((full, depth + 1))
            except Exception:
                pass
        # Save page
        page = CrawlPage(
            job_id=job.id,
            url=url,
            normalized_url=url,
            depth=depth,
            status_code=status_code,
            title=title,
            content_text=text,
        )
        session.add(page)
        session.commit()
        session.refresh(page)
        created += 1
        pages += 1

    stats = {"pages": pages, "created": created}
    job.stats = stats
    return stats
