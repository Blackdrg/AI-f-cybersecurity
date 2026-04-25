#!/bin/bash
#
# AI-f Sandbox Deployment Script
# Deploys a complete sandbox environment for testing and evaluation
#
# Usage: ./deploy_sandbox.sh [--local|--cloud]
#
# Requirements:
# - Docker and Docker Compose
# - 4GB RAM minimum, 8GB recommended
# - 2 CPU cores minimum
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SANDBOX_ENV="sandbox"
DEPLOY_MODE="${1:-local}"
DOMAIN="${SANDBOX_DOMAIN:-sandbox.ai-f.local}"
API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-3000}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   AI-f Sandbox Deployment${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "Mode: ${GREEN}${DEPLOY_MODE}${NC}"
echo -e "Domain: ${GREEN}${DOMAIN}${NC}"
echo -e "API Port: ${GREEN}${API_PORT}${NC}"
echo -e "UI Port: ${GREEN}${UI_PORT}${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}"

# Check resources
TOTAL_MEM=$(docker system info --format '{{.MemTotal}}' 2>/dev/null || echo "0")
if [ "$TOTAL_MEM" -lt 4000000000 ]; then
    echo -e "${YELLOW}⚠️  Warning: Less than 4GB RAM available${NC}"
fi
echo -e "${GREEN}✓ System resources OK${NC}"
echo ""

# Generate SSL certificates for local HTTPS
echo -e "${YELLOW}Generating SSL certificates...${NC}"
mkdir -p certs

if [ ! -f certs/localhost.pem ] || [ ! -f certs/localhost-key.pem ]; then
    openssl req -x509 -newkey rsa:4096 -keyout certs/localhost-key.pem \
        -out certs/localhost.pem -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=AI-f/CN=${DOMAIN}" 2>/dev/null || true
    echo -e "${GREEN}✓ SSL certificates generated${NC}"
else
    echo -e "${GREEN}✓ SSL certificates already exist${NC}"
fi
echo ""

# Create .env file for sandbox
echo -e "${YELLOW}Creating sandbox configuration...${NC}"
cat > infra/.env.sandbox << EOF
# Sandbox Environment Configuration
ENVIRONMENT=sandbox
DEBUG=true

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=ai_f_sandbox
DB_USER=ai_f_admin
DB_PASSWORD=SandboxPass123!
DB_READ_REPLICAS=postgres-replica-1:5432

# Redis Configuration
REDIS_URL=redis://redis:6379

# JWT Configuration
JWT_SECRET=SandboxJWTSecretKey2024ChangeInProduction
JWT_EXPIRATION_HOURS=24

# Encryption
ENCRYPTION_KEY=SandboxEncryptionKey2024ChangeInProduction!!

# API Configuration
API_URL=https://${DOMAIN}:${API_PORT}
CORS_ORIGINS=https://${DOMAIN}:${UI_PORT},http://localhost:3000

# Storage
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=10485760

# Monitoring
ENABLE_METRICS=true
ENABLE_PROMETHEUS=true

# Features
ENABLE_SPOOF_DETECTION=true
ENABLE_MULTI_MODAL=true
ENABLE_ANALYTICS=true

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Email (for notifications)
SMTP_HOST=smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=sandbox
SMTP_PASS=sandbox

# Security
ENABLE_AUDIT_LOG=true
AUDIT_LOG_RETENTION_DAYS=90
SESSION_TIMEOUT_MINUTES=60

# Feature Flags
FEATURE_FLAG_SDK_V2=true
FEATURE_FLAG_ADVANCED_ANALYTICS=true
FEATURE_FLAG_CUSTOM_POLICIES=true
EOF

echo -e "${GREEN}✓ Sandbox configuration created${NC}"
echo ""

# Build and start services
echo -e "${YELLOW}Building and starting services...${NC}"
echo ""

if [ "$DEPLOY_MODE" == "cloud" ]; then
    echo -e "${BLUE}Deploying cloud-optimized configuration...${NC}"
    docker compose -f infra/docker-compose.yml -f infra/docker-compose.sandbox.yml up -d --build
else
    echo -e "${BLUE}Deploying local development configuration...${NC}"
    docker compose -f infra/docker-compose.yml -f infra/docker-compose.sandbox.yml up -d --build
fi

echo ""
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -k -s -o /dev/null -w "%{http_code}" https://localhost:${API_PORT}/api/health | grep -q "200"; then
        echo -e "${GREEN}✓ API is healthy${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -en "."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Services failed to start${NC}"
    docker compose -f infra/docker-compose.yml logs backend
    exit 1
fi

echo ""
echo -e "${GREEN}✓ All services are ready!${NC}"
echo ""

# Initialize database with sample data
echo -e "${YELLOW}Initializing database with sample data...${NC}"
sleep 5

# Create admin user
curl -k -s -X POST https://localhost:${API_PORT}/api/users \
    -H "Content-Type: application/json" \
    -d '{
        "email": "admin@sandbox.ai-f.io",
        "name": "Sandbox Admin",
        "subscription_tier": "enterprise"
    }' > /dev/null 2>&1 || true

# Create sample persons
curl -k -s -X POST https://localhost:${API_PORT}/api/persons \
    -H "Content-Type: application/json" \
    -d '{
        "name": "John Doe",
        "age": 30,
        "gender": "M"
    }' > /dev/null 2>&1 || true

echo -e "${GREEN}✓ Sample data created${NC}"
echo ""

# Display access information
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Sandbox Deployment Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}Access URLs:${NC}"
echo -e "  🌐 Admin Dashboard:  https://localhost:${UI_PORT}"
echo -e "  🔧 API Documentation: https://localhost:${API_PORT}/docs"
echo -e "  📊 Health Check:     https://localhost:${API_PORT}/api/health"
echo -e "  📈 Metrics:          https://localhost:${API_PORT}/metrics"
echo ""
echo -e "${GREEN}Credentials:${NC}"
echo -e "  📧 Email:    admin@sandbox.ai-f.io"
echo -e "  🔐 Password: Use JWT token from API response"
echo ""
echo -e "${GREEN}Quick Start:${NC}"
echo -e "  1. Access the dashboard: https://localhost:${UI_PORT}"
echo -e "  2. Explore API docs: https://localhost:${API_PORT}/docs"
echo -e "  3. Run sample recognition:"
echo -e "     curl -k -X POST https://localhost:${API_PORT}/api/recognize \\"
echo -e "          -F 'image=@sample.jpg'"
echo ""
echo -e "${GREEN}SDK Installation:${NC}"
echo -e "  pip install ai-f-sdk"
echo ""
echo -e "${GREEN}Useful Commands:${NC}"
echo -e "  🐳 View logs:    docker compose -f infra/docker-compose.yml logs -f"
echo -e "  🛑 Stop:         docker compose -f infra/docker-compose.yml down"
echo -e "  🔄 Restart:      docker compose -f infra/docker-compose.yml restart"
echo -e "  📊 Monitor:      docker compose -f infra/docker-compose.yml top"
echo ""
echo -e "${GREEN}Security Note:${NC}"
echo -e "  🔒 This is a ${YELLOW}sandbox${NC} environment with self-signed certificates."
echo -e "  🔒 Do not use in production. Change all passwords and keys."
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo -e "  1. Review SOC 2 assessment: SOC2_TYPE_II_GAP_ASSESSMENT.md"
echo -e "  2. Review DPIA: DPIA_DATA_PROTECTION_IMPACT_ASSESSMENT.md"
echo -e "  3. Run security scan: python security/owasp_zap_scan.py --target https://localhost:${API_PORT}"
echo -e "  4. Run benchmarks: pytest backend/tests/test_benchmark.py"
echo ""
echo -e "${BLUE}Happy coding! 🚀${NC}"
