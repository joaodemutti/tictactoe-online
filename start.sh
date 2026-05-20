#!/bin/bash
set -e

# Convert postgres:// to postgresql+asyncpg:// if Render provides the standard URL
export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|postgres://|postgresql+asyncpg://|g' | sed 's|postgresql://|postgresql+asyncpg://|g')

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
