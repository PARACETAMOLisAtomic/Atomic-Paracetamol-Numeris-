#!/bin/bash
echo "Stopping services..."
pkill -f celery
pkill -f uvicorn
pkill -f "npm run dev"
docker-compose -f docker/docker-compose.yml down
echo "All services stopped."
