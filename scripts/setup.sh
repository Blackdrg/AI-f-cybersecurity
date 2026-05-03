#!/bin/bash
# AI-F One-Command Setup (Cross-platform, Docker-only fallback)

set -e

echo "🚀 Starting AI-F Enterprise Platform setup (Windows/Linux/Mac)..."

# Check if docker compose available
if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
  echo "❌ Docker required. Install from https://docker.com"
  exit 1
fi

# 2. Frontend build (host if node, else nginx in compose)
if command -v npm &> /dev/null; then
  echo "Building frontend..."
  cd ui/react-app
  npm ci
  npm run build
  cd ../..
fi

# 3. Docker compose full stack
echo "Starting full stack with Docker Compose..."
docker compose -f infra/docker-compose.full.yml up -d --build

# 4. Wait healthy
echo "Waiting for healthy..."
for i in {1..10}; do
  if curl -f http://localhost:8000/healthz >/dev/null 2>&1; then
    break
  fi
  sleep 10
done

curl http://localhost:8000/healthz

echo "✅ Setup complete!"
echo "API: http://localhost:8000/healthz"
echo "UI: http://localhost:3000 (or serve ui/react-app/build)"
echo "Logs: docker compose logs -f"
echo "Stop: docker compose down"
echo "Prod: See docs/DEPLOY.md"

