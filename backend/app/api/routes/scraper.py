from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import get_current_active_superuser
from app.core.db import engine
from app.models import ScrapedPost, ScrapedPostPublic, ScrapedPostsPublic
from app.scraper.runner import run_scraping_for_company

router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.post(
    "/run/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def run_scraper(companies: list[str] = Query(default=[])) -> dict[str, Any]:
    if not companies:
        raise HTTPException(status_code=400, detail="Provide at least one company name")

    results: dict[str, Any] = {}
    with Session(engine) as session:
        for company in companies:
            summary = run_scraping_for_company(session=session, company=company)
            results[company] = summary
    return {"results": results}


@router.get("/posts/", response_model=ScrapedPostsPublic)
def list_posts(
    company: str | None = None,
    platform: str | None = None,
    limit: int = 50,
    offset: int = 0,
    newer_than: datetime | None = None,
) -> ScrapedPostsPublic:
    with Session(engine) as session:
        statement = select(ScrapedPost)
        if company:
            statement = statement.where(ScrapedPost.company == company)
        if platform:
            statement = statement.where(ScrapedPost.platform == platform)
        if newer_than:
            statement = statement.where(ScrapedPost.published_at >= newer_than)
        statement = statement.order_by(ScrapedPost.published_at.desc(), ScrapedPost.fetched_at.desc())
        items = session.exec(statement.offset(offset).limit(limit)).all()
        count = session.exec(statement).count()  # type: ignore[attr-defined]
        data = [ScrapedPostPublic.model_validate(i) for i in items]
        return ScrapedPostsPublic(data=data, count=count)
