#!/bin/bash
set -e

# Normalize the driver if a plain postgres:// / postgresql:// URL is provided
export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|postgres://|postgresql+asyncpg://|g' | sed 's|postgresql://|postgresql+asyncpg://|g')

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
