#!/bin/bash
# LEVI-AI Enterprise One-Click Installer
# Targets: Ubuntu 20.04+, Debian 11+

set -e

echo "--- LEVI-AI Enterprise Installation Started ---"

# 1. Update & Prereqs
sudo apt-get update
sudo apt-get install -y curl git docker.io docker-compose python3-pip

# 2. Clone Repository (if not already in dir)
if [ ! -d "AI-f" ]; then
  git clone https://github.com/Blackdrg/AI-f-cybersecurity.git AI-f
  cd AI-f
fi

# 3. Setup Environment
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "GENERIC_SECRET=$(openssl rand -hex 32)" >> .env
  echo "Created .env with random secrets. Please update with your Stripe/AWS keys."
fi

# 4. Start Services
cd infra
sudo docker-compose pull
sudo docker-compose up -d

# 5. Verify
echo "Waiting for services to stabilize..."
sleep 10
curl -f http://localhost:8000/health || (echo "Backend failed to start" && exit 1)

echo "--- Installation Complete! ---"
echo "API Docs: http://localhost:8000/docs"
echo "Dashboard: http://localhost:3000"
echo "Default Admin: admin@levi-ai.com / admin123"
