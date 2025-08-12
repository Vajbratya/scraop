from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select, func

from app.api.deps import get_current_active_superuser
from app.api.deps import require_api_key, require_ip_allowlist
from app.core.db import engine
from app.core.config import settings
from app.models import ScrapedPost, ScrapedPostPublic, ScrapedPostsPublic, ScrapeJob, ScrapeJobPublic, CrawlPage, CrawlPagesPublic
from app.scraper.runner import run_scraping_for_company, bfs_crawl
import httpx
from pydantic import BaseModel, Field

router = APIRouter(prefix="/scraper", tags=["scraper"])


async def _notify_slack(message: str) -> None:
    if not settings.SLACK_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(str(settings.SLACK_WEBHOOK_URL), json={"text": message})
    except Exception:
        return


class CreateJobIn(BaseModel):
    name: str = Field(max_length=255)
    seeds: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    max_depth: int = 2
    max_pages: int = 100
    render_js: bool = False
    webhook_url: str | None = None


class JobsOut(BaseModel):
    data: list[ScrapeJobPublic]
    count: int


@router.get("/jobs/", response_model=JobsOut, dependencies=[Depends(require_ip_allowlist), Depends(require_api_key), Depends(get_current_active_superuser)])
async def list_jobs(limit: int = 50, offset: int = 0) -> JobsOut:
    with Session(engine) as session:
        stmt = select(ScrapeJob).offset(offset).limit(limit).order_by(ScrapeJob.created_at.desc())
        items = session.exec(stmt).all()
        # count simple
        count = session.exec(select(func.count()).select_from(ScrapeJob)).one()
        return JobsOut(data=[ScrapeJobPublic.model_validate(i) for i in items], count=count)


@router.get("/jobs/{job_id}", response_model=ScrapeJobPublic, dependencies=[Depends(require_ip_allowlist), Depends(require_api_key), Depends(get_current_active_superuser)])
async def get_job(job_id: str) -> ScrapeJobPublic:
    from uuid import UUID

    with Session(engine) as session:
        job = session.get(ScrapeJob, UUID(job_id))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return ScrapeJobPublic.model_validate(job)


@router.delete("/jobs/{job_id}", dependencies=[Depends(require_ip_allowlist), Depends(require_api_key), Depends(get_current_active_superuser)])
async def delete_job(job_id: str) -> dict[str, Any]:
    from uuid import UUID

    with Session(engine) as session:
        job = session.get(ScrapeJob, UUID(job_id))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        session.delete(job)
        session.commit()
        return {"message": "Job deleted"}


@router.post("/jobs/", response_model=ScrapeJobPublic, dependencies=[Depends(require_ip_allowlist), Depends(require_api_key), Depends(get_current_active_superuser)])
async def create_job(payload: CreateJobIn) -> ScrapeJobPublic:
    with Session(engine) as session:
        job = ScrapeJob.model_validate(payload)
        session.add(job)
        session.commit()
        session.refresh(job)
        return ScrapeJobPublic.model_validate(job)


@router.post("/jobs/{job_id}/run", dependencies=[Depends(require_ip_allowlist), Depends(require_api_key), Depends(get_current_active_superuser)])
async def run_job(job_id: str) -> dict[str, Any]:
    from uuid import UUID

    with Session(engine) as session:
        job = session.get(ScrapeJob, UUID(job_id))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        job.status = "running"
        job.started_at = datetime.utcnow()
        session.add(job)
        session.commit()
        stats = bfs_crawl(session=session, job=job)
        job.status = "finished"
        job.finished_at = datetime.utcnow()
        job.stats = stats
        session.add(job)
        session.commit()
        await _notify_slack(f"[JOB] {job.name} finished: {stats}")
        if job.webhook_url:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(job.webhook_url, json={"job_id": str(job.id), "stats": stats})
            except Exception:
                pass
        return {"job_id": str(job.id), "stats": stats}


@router.get("/jobs/{job_id}/pages", response_model=CrawlPagesPublic, dependencies=[Depends(require_ip_allowlist), Depends(require_api_key), Depends(get_current_active_superuser)])
async def list_job_pages(job_id: str, limit: int = 100, offset: int = 0) -> CrawlPagesPublic:
    from uuid import UUID

    with Session(engine) as session:
        statement = select(CrawlPage).where(CrawlPage.job_id == UUID(job_id)).offset(offset).limit(limit)
        pages = session.exec(statement).all()
        return CrawlPagesPublic(data=[p for p in pages], count=len(pages))


@router.post(
    "/run/",
    dependencies=[Depends(require_ip_allowlist), Depends(require_api_key), Depends(get_current_active_superuser)],
    status_code=201,
)
async def run_scraper(companies: list[str] = Query(default=[])) -> dict[str, Any]:
    if not companies:
        raise HTTPException(status_code=400, detail="Provide at least one company name")

    results: dict[str, Any] = {}
    inserted_total = 0
    with Session(engine) as session:
        for company in companies:
            summary = run_scraping_for_company(session=session, company=company)
            results[company] = summary
            inserted_total += int(summary.get("inserted", 0))
    await _notify_slack(f"Scraper run completed for {', '.join(companies)}: {inserted_total} new/updated items")
    return {"results": results}


@router.post("/run-cron/", status_code=201)
async def run_scraper_cron(request: Request, companies: list[str] = Query(default=[]), token: str | None = None) -> dict[str, Any]:
    auth_token = token or request.headers.get("X-Cron-Token")
    if not settings.SCRAPER_CRON_TOKEN or auth_token != settings.SCRAPER_CRON_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid cron token")
    if not companies:
        companies = ["laudite", "laudos.ai", "laudos", "leorad"]
    results: dict[str, Any] = {}
    inserted_total = 0
    with Session(engine) as session:
        for company in companies:
            summary = run_scraping_for_company(session=session, company=company)
            results[company] = summary
            inserted_total += int(summary.get("inserted", 0))
    await _notify_slack(f"[CRON] Scraper run completed for {', '.join(companies)}: {inserted_total} items")
    return {"results": results, "scheduled": True}


@router.get("/posts/", response_model=ScrapedPostsPublic)
async def list_posts(
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
        count = len(items)
        data = [ScrapedPostPublic.model_validate(i) for i in items]
        return ScrapedPostsPublic(data=data, count=count)
