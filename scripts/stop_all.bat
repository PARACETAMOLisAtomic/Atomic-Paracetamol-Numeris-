@echo off
echo Stopping services...
taskkill /F /IM celery.exe /T
taskkill /F /IM uvicorn.exe /T
taskkill /F /IM node.exe /T
docker-compose -f docker\docker-compose.yml down
echo All services stopped.
