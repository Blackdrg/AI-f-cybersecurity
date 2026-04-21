#!/bin/bash

# Run POC with docker-compose

# Exit immediately if a command exits with a non-zero status
set -e

# Change to infra directory
cd infra

# Build and start the containers in the background
docker-compose up --build -d

# Wait for containers to be healthy (optional: uncomment if healthchecks are defined)
# echo "Waiting for containers to be healthy..."
# docker-compose ps

echo "POC containers are up and running!"