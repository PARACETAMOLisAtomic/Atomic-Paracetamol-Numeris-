@echo off
echo ============================================
echo   Numeris v3.0 - Starting local services
echo ============================================

echo [1/4] Starting Redis via Docker...
docker-compose -f docker\docker-compose.yml up -d
timeout /t 2 /nobreak >nul

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: No .venv found. Run scripts\setup.bat first.
)

echo [2/4] Starting Celery worker...
start cmd /k "title Numeris Celery Worker && celery -A backend.core.celery_app worker --loglevel=info -P solo"

echo [3/4] Starting FastAPI backend on port 8000...
start cmd /k "title Numeris API && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

echo [4/4] Starting Vite frontend on port 5173...
cd frontend
start cmd /k "title Numeris Frontend && npm run dev"
cd ..

echo.
echo FastAPI  ->  http://localhost:8000
echo API docs ->  http://localhost:8000/docs
echo Frontend ->  http://localhost:5173
