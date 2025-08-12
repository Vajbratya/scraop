### Overview

This repository is a full‑stack application consisting of:
- Backend: FastAPI + SQLModel + PostgreSQL
- Frontend: React (Vite) + TanStack Router + TanStack Query + Chakra UI
- Scraping: Lightweight RSS/sitemap ingestion and a Firecrawl‑style BFS crawler
- Extras: Slack notifications, cron‑protected scrape runs, playground cookbooks (PubMed, Perplexity‑like Ask), API hardening (API key + IP allowlist), optional prerender for JS sites

### Key Features
- Auth, users, items (starter app)
- Scraping:
  - Quick ingestion from RSS/sitemaps for startup sites
  - Firecrawl‑style crawler with jobs, BFS traversal, include/exclude regex filters, depth/page caps
  - Optional JS rendering via prerender service (set `RENDER_SERVICE_URL`) when job `render_js=true`
  - Reasonable content scoring (recency/length)
  - Slack webhook notifications on completion
  - Cron‑protected endpoint for scheduled scraping
- Frontend pages:
  - Dashboard, Items CRUD, Settings, Admin
  - Scraper page (superusers): trigger scrapes, filter/sort, auto‑refresh, CSV export
  - Playground: login/token, run/list scrapes; cookbooks (PubMed, Perplexity‑like Ask)
  - API Docs embedded page
- Security hardening:
  - `X-API-Key` header enforcement (if `API_KEY` set)
  - IP allowlist (if `IP_ALLOWLIST` set)

### What’s new (delta from base)
- Models: `ScrapedPost`, `ScrapeJob`, `CrawlPage`
- Router: `/api/v1/scraper/*` (quick run, cron, jobs CRUD/run/pages) with Slack + cron
- Router: `/api/v1/examples/*` (PubMed search/summarize with GPT, Ask with URLs)
- Config: `API_KEY`, `IP_ALLOWLIST`, `SLACK_WEBHOOK_URL`, `SCRAPER_CRON_TOKEN`, `RENDER_SERVICE_URL`, `OPENAI_API_KEY`
- Frontend: `/_layout/scraper` upgraded UX, `/playground` with cookbooks

### Architecture (at a glance)
- Ingestion paths:
  - RSS/sitemap → normalize (score) → `scrapedpost`
  - Job BFS crawl → HTML → text extraction → `crawlpage`
- Scheduling:
  - Cron endpoint (shared‑nothing), optional external cron/Scheduler
  - Slack webhook notifications
- Optional rendering:
  - If `RENDER_SERVICE_URL` and job `render_js=true`, fetch via prerender service

### Project Structure
- `backend/`
  - `app/api/routes/`
    - `scraper.py` (quick run, cron, jobs: create/list/get/delete/run/pages)
    - `examples.py` (pubmed + ask cookbooks)
    - `items.py`, `users.py`, `login.py`, `utils.py`
  - `app/scraper/` (rss, bfs crawler, utils, scoring)
  - `app/models.py` (User/Item/ScrapedPost/ScrapeJob/CrawlPage)
  - `app/core/` (config/db/security)
  - `alembic/versions/` (migrations)
- `frontend/`
  - `src/routes/_layout/scraper.tsx` (polished scraper UI)
  - `src/routes/playground.tsx` (auth + cookbooks + manual scraping)
  - `src/routes/docs.tsx` (embedded swagger)

### Data Models (selected)
- `ScrapedPost` (company, platform, url, title, content, language, published_at, fetched_at, score, metadata)
- `ScrapeJob` (name, seeds, allowed_domains, include_patterns, exclude_patterns, max_depth, max_pages, render_js, webhook_url, status, stats, created/started/finished)
- `CrawlPage` (job_id, url, normalized_url, depth, status_code, title, content_text, score, fetched_at, meta)

### Backend API
- Utils:
  - `GET /api/v1/utils/health-check/`
- Scraper: quick ingestion
  - `POST /api/v1/scraper/run/?companies=laudite&companies=laudos.ai` (superuser + API key/IP allowlist if enabled)
  - `GET /api/v1/scraper/posts/?company=laudite`
- Scraper: cron
  - `POST /api/v1/scraper/run-cron/?companies=...` with header `X-Cron-Token: SCRAPER_CRON_TOKEN`
- Jobs (Firecrawl‑style)
  - `GET /api/v1/scraper/jobs/` (list)
  - `POST /api/v1/scraper/jobs/` (create)
  - `GET /api/v1/scraper/jobs/{job_id}` (get)
  - `DELETE /api/v1/scraper/jobs/{job_id}` (delete)
  - `POST /api/v1/scraper/jobs/{job_id}/run` (execute BFS crawl)
  - `GET /api/v1/scraper/jobs/{job_id}/pages` (list crawled pages)
- Examples
  - `POST /api/v1/examples/pubmed/search` (query, max_results)
  - `POST /api/v1/examples/pubmed/summarize` (pmid) → requires `OPENAI_API_KEY`
  - `POST /api/v1/examples/ask` (question, urls[]) → requires `OPENAI_API_KEY`

### Security & Access Control
- API keys: set `API_KEY` to require `X-API-Key` on sensitive routes (scraper/jobs)
- IP allowlist: set `IP_ALLOWLIST=["1.2.3.4"]` to restrict requests by `Request.client.host`
- Cron: set `SCRAPER_CRON_TOKEN`, required by `/scraper/run-cron`
- Users: superuser required for scraper/job endpoints

### Configuration (backend .env)
Required for local/dev:
- `POSTGRES_SERVER`, `POSTGRES_PORT=5432`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `FIRST_SUPERUSER`, `FIRST_SUPERUSER_PASSWORD`
- `FRONTEND_HOST` (e.g. `http://localhost:5173`)
- `BACKEND_CORS_ORIGINS=["http://localhost:5173"]`
Optional:
- `OPENAI_API_KEY` → enables LLM cookbook endpoints
- `SLACK_WEBHOOK_URL` → Slack notifications
- `SCRAPER_CRON_TOKEN` → protect `/scraper/run-cron`
- `API_KEY`, `IP_ALLOWLIST=["..."]` → API hardening
- `RENDER_SERVICE_URL` → prerender base to support JS (e.g. https://rendertron.yourhost)
- `SENTRY_DSN` → error monitoring

### Running Locally
With Docker (recommended):
```bash
# from repo root
cp .env.example .env  # if you have one, else create .env with the variables above
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000, docs at /docs
```
Without Docker:
- Backend: Python 3.10+, `uv sync`, `uv run fastapi run app/main.py --port 8000`
- Frontend: `cd frontend && npm ci && VITE_API_URL=http://localhost:8000 npm run dev`

### Frontend
- `/_layout/scraper`: run (buttons per company, scrape-all), filters (company/platform), sort (newest/score/title), auto‑refresh 60s, CSV export
- `/playground`: set API base, login, run/list scrapes; cookbooks: PubMed search/summarize, Ask with URLs
- `/docs`: embed Swagger UI

### Scoring & Ingestion
- RSS/sitemap ingestion:
  - Discover feeds via `<link type="application/rss+xml">` and common feed paths
  - Fallback to sitemaps
  - Score: recency half‑life (~90d) + content length up to ~4k chars
- BFS crawling:
  - Queue of URLs (seed), visited set, domain allow‑list, include/exclude regex filters
  - Depth/page limits
  - Extract title and raw text; persist pages to `crawlpage`
  - Optional JS prerender when `render_js=true` and `RENDER_SERVICE_URL` configured

### Notifications & Scheduling
- Slack: If `SLACK_WEBHOOK_URL` is set, scraper/job completion posts to Slack
- Cron: `POST /api/v1/scraper/run-cron` with `X-Cron-Token`. Example crontab hourly:
```bash
0 * * * * curl -s -X POST "http://YOUR_HOST:8000/api/v1/scraper/run-cron/?companies=laudite&companies=laudos.ai" -H "X-Cron-Token: YOUR_TOKEN" >/dev/null 2>&1
```

### Deployment
- VPS + Docker Compose (fastest):
  - Set `.env`, run compose with override for local ports
  - Frontend: `5173`, Backend: `8000`
- Hosted free tiers:
  - Backend: Render/Fly.io/Railway
  - DB: Supabase/Neon (free Postgres)
  - Frontend: Cloudflare Pages/Netlify (build with `VITE_API_URL`)
- Custom domain + TLS:
  - Traefik config in `docker-compose.yml`, set `DOMAIN`, DNS for `api.<domain>` and `dashboard.<domain>`

### Example cURL
- Quick scraper (superuser token + optional API key):
```bash
curl -s -X POST "http://localhost:8000/api/v1/scraper/run/?companies=laudite" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "X-API-Key: <API_KEY>"
```
- Create + run job:
```bash
curl -s -X POST http://localhost:8000/api/v1/scraper/jobs/ \
  -H "Authorization: Bearer <TOKEN>" -H "X-API-Key: <API_KEY>" -H "Content-Type: application/json" \
  -d '{
    "name": "laudite-crawl",
    "seeds": ["https://laudite.com.br/"],
    "allowed_domains": ["laudite.com.br"],
    "exclude_patterns": ["\\.pdf$"],
    "max_depth": 2,
    "max_pages": 100,
    "render_js": false
  }'
# Then run
curl -s -X POST http://localhost:8000/api/v1/scraper/jobs/<job_id>/run \
  -H "Authorization: Bearer <TOKEN>" -H "X-API-Key: <API_KEY>"
```

### Testing
- Backend tests: `bash ./scripts/test.sh` (Docker)
- Frontend E2E: requires backend; see `frontend/tests` and `Dockerfile.playwright`

### Code Style & Conventions
- Python: typed, SQLModel, Pydantic v2, guard clauses, no over‑catching, match repo formatters (ruff)
- TS/React: TanStack Router/Query, Chakra, clear prop types, minimal global state; prefer fetch with OpenAPI.BASE

### For another AI agent (how to proceed)
- Add a UI for Jobs:
  - Route under `/_layout/jobs`: list (GET /scraper/jobs), create (POST), run (POST {id}/run), delete (DELETE), pages (GET {id}/pages)
  - Use superuser guard and show status chips; CSV/JSON export for pages
- Add a background worker:
  - New service (e.g., `worker/`) with Celery or RQ + Redis
  - Update `/jobs/{id}/run` to enqueue; add `/jobs/{id}/status`
  - Add Playwright rendering (Node/Playwright container) or Python `playwright` to fetch HTML when `render_js`
- Add source‑specific connectors (LinkedIn/X/YouTube) respecting ToS using official APIs
- Add search indexing (Meilisearch/Typesense) for `scrapedpost` and `crawlpage`
- Improve scoring (canonical URL normalization, dedupe, engagement signals)
- Update alembic migration when models change; ensure tests pass (`backend/scripts/test.sh`)

This document summarizes architecture, endpoints, configuration, and practical operations for this app, and includes guidance for further implementation. Use the code locations listed and the OpenAPI at `/docs` to continue development.
