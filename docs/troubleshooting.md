# Troubleshooting Guide

## Docker Issues
1. Docker Desktop running? Start it.
2. **APT / Network failures**: Fixed with HTTPS bookworm sources in backend/Dockerfile & backend/app/Dockerfile.
3. Env vars: cp infra/.env.example infra/.env , edit DB_PASSWORD etc.
4. Build GPU: docker compose --build up -d (USE_GPU=true in .env)
5. Logs: docker compose logs backend
6. Test build: docker build -f backend/Dockerfile . && docker build -f backend/app/Dockerfile backend/app
7. Windows DNS: Docker Settings > DNS ["8.8.8.8", "1.1.1.1"]

## Backend Errors
1. DB conn fail: Check postgres logs, DB_PASSWORD set.
2. Models download: First run downloads insightface ~500MB.

## UI Issues
1. Proxy: setupProxy.js points to :8000
2. WS: localhost:8000/ws/stream_recognize

## Podman
1. podman-compose up -d (after pip install podman-compose)

## Common
- Free port 80/443/nginx conflict → change ports
- GPU: nvidia-docker support or USE_GPU=false
