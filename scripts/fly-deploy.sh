#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   BACKEND_APP=scraop-backend FRONTEND_APP=scraop-frontend REGION=gig \
#   FIRST_SUPERUSER=admin@example.com FIRST_SUPERUSER_PASSWORD='changeme' \
#   VITE_API_URL=https://scraop-backend.fly.dev \
#   ./scripts/fly-deploy.sh
#
# Requires: flyctl logged in (flyctl auth login)

: "${BACKEND_APP:?Set BACKEND_APP}"
: "${FRONTEND_APP:?Set FRONTEND_APP}"
REGION="${REGION:-gig}"
VITE_API_URL="${VITE_API_URL:-}"
FIRST_SUPERUSER="${FIRST_SUPERUSER:-admin@example.com}"
FIRST_SUPERUSER_PASSWORD="${FIRST_SUPERUSER_PASSWORD:-changeme}"
SECRET_KEY="${SECRET_KEY:-$(openssl rand -base64 32 2>/dev/null || echo supersecret)}"
SCRAPER_CRON_TOKEN="${SCRAPER_CRON_TOKEN:-$(openssl rand -hex 32 2>/dev/null || echo cronsecret)}"
API_KEY="${API_KEY:-$(openssl rand -hex 32 2>/dev/null || echo apikeysecret)}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

# 1) Backend app
flyctl apps create "$BACKEND_APP" || true

# 2) Fly Postgres (Lite) and attach
DB_NAME="${BACKEND_APP}-db"
flyctl postgres create --name "$DB_NAME" --region "$REGION" --vm-size shared-cpu-1x --volume-size 1 --initial-cluster-size 1 || true
flyctl postgres attach "$DB_NAME" --app "$BACKEND_APP" || true

# 3) Secrets
FRONTEND_ORIGIN="https://${FRONTEND_APP}.fly.dev"
CORS_JSON="[\"${FRONTEND_ORIGIN}\"]"
SECRETS=(
  "SECRET_KEY=${SECRET_KEY}"
  "FIRST_SUPERUSER=${FIRST_SUPERUSER}"
  "FIRST_SUPERUSER_PASSWORD=${FIRST_SUPERUSER_PASSWORD}"
  "FRONTEND_HOST=${FRONTEND_ORIGIN}"
  "BACKEND_CORS_ORIGINS=${CORS_JSON}"
  "SCRAPER_CRON_TOKEN=${SCRAPER_CRON_TOKEN}"
  "API_KEY=${API_KEY}"
)

if [ -n "$OPENAI_API_KEY" ]; then SECRETS+=("OPENAI_API_KEY=${OPENAI_API_KEY}"); fi
if [ -n "$SLACK_WEBHOOK_URL" ]; then SECRETS+=("SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}"); fi

printf '%s
' "${SECRETS[@]}" | flyctl secrets set --app "$BACKEND_APP"

# 4) Deploy backend
flyctl deploy --config backend/fly.toml --app "$BACKEND_APP" --region "$REGION"

# 5) Frontend app
flyctl apps create "$FRONTEND_APP" || true
: "${VITE_API_URL:=https://${BACKEND_APP}.fly.dev}"
# 6) Deploy frontend with API base
flyctl deploy --config frontend/fly.toml --app "$FRONTEND_APP" --region "$REGION" \
  --build-arg "VITE_API_URL=${VITE_API_URL}"

echo "\nDeployed:"
echo "Backend: https://${BACKEND_APP}.fly.dev (docs at /docs)"
echo "Frontend: https://${FRONTEND_APP}.fly.dev (playground at /playground)"
