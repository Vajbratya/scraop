from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.models import ScrapedPost
from .website import normalize_entries, scrape_homepage_sources

DEFAULT_SOURCES: dict[str, dict[str, Any]] = {
    # You can expand or override these via API or config later
    "laudos.ai": {"homepage": "https://laudos.ai/"},
    "laudos": {"homepage": "https://home.laudos.ai/"},
    "laudite": {"homepage": "https://laudite.com.br/"},
    "leorad": {"homepage": "https://leorad.com/"},  # placeholder, may 404 if non-existent
}


def upsert_post(session: Session, data: dict[str, Any]) -> bool:
    existing = session.exec(select(ScrapedPost).where(ScrapedPost.url == data["url"])).first()
    if existing:
        # Update score and timestamps if we fetched again
        changed = False
        if data.get("title") and existing.title != data["title"]:
            existing.title = data["title"]
            changed = True
        if data.get("content") and existing.content != data["content"]:
            existing.content = data["content"]
            changed = True
        if data.get("published_at") and existing.published_at != data["published_at"]:
            existing.published_at = data["published_at"]
            changed = True
        if data.get("score") is not None and existing.score != data["score"]:
            existing.score = float(data["score"])  # ensure type
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
    updated = 0
    for e in entries:
        changed = upsert_post(session, e)
        if changed:
            # We cannot easily distinguish insert vs update without additional query cost
            inserted += 1
    return {"inserted": inserted, "updated": updated, "source": homepage}
