#!/bin/bash
# AI-F Infrastructure Setup Script
# Bash script for Linux/macOS development environment
# Installs and configures PostgreSQL 15 + pgvector, Redis 7, and all dependencies

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_header() {
    echo -e "${CYAN}=== $1 ===${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

# Check prerequisites
log_header "Checking Prerequisites"

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "Docker Compose is not installed."
    exit 1
fi

log_success "Docker is available"

# Create necessary directories
log_header "Creating directories"

DIRS=(
    "backend/models/onnx_bundle"
    "backend/data"
    "backend/logs"
    "backend/data/uploads"
)

for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "Created: $dir"
    fi
done

# Copy environment file
log_header "Configuring environment"

if [ -f "infra/.env" ]; then
    cp infra/.env .env
    log_success "Environment file configured"
fi

# Start infrastructure services
log_header "Starting Infrastructure Services"

cd infra

# Start PostgreSQL
echo "Starting PostgreSQL 15 + pgvector..."
docker-compose up -d postgres
log_success "PostgreSQL container started"

# Start Redis
echo "Starting Redis 7 cluster..."
docker-compose up -d redis-master redis-replica
log_success "Redis containers started"

# Wait for services
echo "Waiting for services to be ready..."
sleep 15

# Check PostgreSQL
echo "Checking PostgreSQL..."
if docker exec ai-f-postgres-1 pg_isready -U postgres 2>/dev/null; then
    log_success "PostgreSQL is ready"
else
    log_warning "PostgreSQL still starting..."
    sleep 10
fi

# Check Redis
echo "Checking Redis..."
if docker exec ai-f-redis-master-1 redis-cli ping 2>/dev/null | grep -q "PONG"; then
    log_success "Redis is ready"
else
    log_warning "Redis still starting..."
fi

cd ..

# Check GeoIP database
log_header "GeoIP Database"

GEOIP_PATH="backend/data/GeoLite2-City.mmdb"
if [ ! -f "$GEOIP_PATH" ]; then
    echo "GeoIP database not found."
    echo "Download from: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data"
    echo "Place GeoLite2-City.mmdb in: $GEOIP_PATH"
else
    log_success "GeoIP database found"
fi

# Summary
log_header "Setup Complete"

cat << 'EOF'
Infrastructure Status:
  - PostgreSQL 15 + pgvector: Running on port 5432
  - Redis 7 Master: Running on port 6379
  - Redis 7 Replica: Running on port 6380

Next Steps:
  1. Add your API keys to infra/.env
  2. Download GeoIP database (optional)
  3. Run: cd infra && docker-compose up -d backend ui
  4. Run: pytest backend/tests/

To start the backend:
  cd infra
  docker-compose up -d backend

To run tests:
  pytest backend/tests/ -v --tb=short
EOF

echo -e "${GREEN}Infrastructure setup complete!${NC}"