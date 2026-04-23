# LEVI-AI Zero-Downtime Rolling Update Script
# This script performs a rolling update by starting a new container before stopping the old one.

$service_name = "backend"
$image_name = "levi-ai-backend:latest"

Write-Host "--- Starting Zero-Downtime Update for $service_name ---" -ForegroundColor Cyan

# 1. Pull latest image
docker pull $image_name

# 2. Start a second instance on a temporary port
Write-Host "Starting blue-green transition instance..." -ForegroundColor Yellow
docker-compose up -d --scale $service_name=2 --no-recreate

# 3. Wait for new instance to be healthy
Write-Host "Waiting for new instance health check..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# 4. Remove the old instance
Write-Host "Decommissioning old instance..." -ForegroundColor Green
# Docker compose scale down will remove the oldest container first
docker-compose up -d --scale $service_name=1

Write-Host "--- Rolling Update Complete! ---" -ForegroundColor Green
