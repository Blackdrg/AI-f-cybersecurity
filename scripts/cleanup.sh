#!/bin/bash
# Clean up Python virtual environments
Remove-Item -Recurse -Force "backend\venv", "backend\venv311", "backend\venv311_new", "backend\__pycache__", "backend\.pytest_cache" 2>&1
# Clean up Infra Docker volumes
docker volume prune -f 2>&1 || true
# Clean up unused Docker images
docker image prune -af 2>&1 || true
