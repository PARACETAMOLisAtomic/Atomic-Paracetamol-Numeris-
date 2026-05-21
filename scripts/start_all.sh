#!/usr/bin/env bash
set -euo pipefail

echo "Numeris v3.0 - Starting local services"
docker-compose -f docker/docker-compose.yml up -d
source .venv/bin/activate
celery -A backend.core.celery_app worker --loglevel=info &
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
(cd frontend && npm run dev)
