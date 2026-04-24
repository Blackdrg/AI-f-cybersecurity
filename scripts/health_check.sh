#!/bin/bash
#
# AI-f Health Check Script
# Quick verification of all system components
#

set -e

echo "=========================================="
echo "AI-f Health Check"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

check() {
    local name="$1"
    local result="$2"
    
    if [ "$result" = "0" ]; then
        echo -e "${GREEN}✓${NC} $name"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $name"
        ((FAIL++))
    fi
}

warn() {
    local name="$1"
    echo -e "${YELLOW}⚠${NC} $name"
    ((WARN++))
}

# 1. Check Python environment
echo "--- Python Environment ---"
python3 --version > /dev/null 2>&1 && check "Python 3 available" 0 || check "Python 3 available" 1

# Check backend dependencies
cd backend
if [ -f "requirements.txt" ]; then
    echo "Checking key Python packages..."
    python3 -c "import fastapi" 2>/dev/null && check "FastAPI" 0 || check "FastAPI" 1
    python3 -c "import asyncpg" 2>/dev/null && check "asyncpg (PostgreSQL)" 0 || warn "asyncpg missing (offline mode)"
    python3 -c "import redis" 2>/dev/null && check "redis-py" 0 || warn "redis-py missing"
    python3 -c "import faiss" 2>/dev/null && check "FAISS" 0 || warn "FAISS missing (brute-force fallback)"
    python3 -c "import torch" 2>/dev/null && check "PyTorch" 0 || warn "PyTorch missing (CPU only)"
    python3 -c "import cv2" 2>/dev/null && check "OpenCV" 0 || warn "OpenCV missing"
    python3 -c "import insightface" 2>/dev/null && check "InsightFace" 0 || warn "InsightFace missing (mock embeddings)"
    python3 -c "from fer import FER" 2>/dev/null && check "FER (Emotion)" 0 || warn "FER missing"
fi
cd ..

# 2. Check Docker services (if applicable)
echo ""
echo "--- Docker Services ---"
if command -v docker &> /dev/null; then
    docker ps --format "{{.Names}}\t{{.Status}}" | grep -q "Up" && check "Docker containers running" 0 || warn "No running containers"
    
    # Check specific services
    docker ps --format "{{.Names}}" | grep -q "postgres" && check "PostgreSQL container" 0 || warn "PostgreSQL container not running"
    docker ps --format "{{.Names}}" | grep -q "redis" && check "Redis container" 0 || warn "Redis container not running"
    docker ps --format "{{.Names}}" | grep -q "backend" && check "Backend container" 0 || warn "Backend container not running"
    docker ps --format "{{.Names}}" | grep -q "ui" && check "Frontend container" 0 || warn "Frontend container not running"
else
    warn "Docker not installed"
fi

# 3. Check network ports
echo ""
echo "--- Network Ports ---"
check_port() {
    local host="$1"
    local port="$2"
    local name="$3"
    
    if command -v nc &> /dev/null; then
        nc -z -w1 "$host" "$port" 2>/dev/null && check "$name (:$port)" 0 || check "$name (:$port)" 1
    elif command -v timeout &> /dev/null; then
        timeout 1 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null && check "$name (:$port)" 0 || check "$name (:$port)" 1
    else
        warn "netcat/timeout not available for port check"
    fi
}

check_port "localhost" 5432 "PostgreSQL"
check_port "localhost" 6379 "Redis"
check_port "localhost" 8000 "API (HTTP)"
check_port "localhost" 3000 "Frontend"
check_port "localhost" 50051 "gRPC"

# 4. Check database schema
echo ""
echo "--- Database Schema ---"
cd backend
if python3 -c "import asyncpg" 2>/dev/null; then
    python3 -c "
import asyncio, asyncpg, os
async def check():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'password'),
            database=os.getenv('DB_NAME', 'face_recognition'),
            timeout=3
        )
        tables = await conn.fetch('''
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' ORDER BY table_name
        ''')
        print(f'Connected. Found {len(tables)} tables.')
        await conn.close()
    except Exception as e:
        print(f'Connection failed: {e}')
asyncio.run(check())
" 2>/dev/null && check "Database connection & tables" 0 || check "Database connection" 1
fi
cd ..

# 5. Check file permissions
echo ""
echo "--- File Permissions ---"
if [ -f "scripts/diagnostics.py" ]; then
    check "Diagnostic script exists" 0
    [ -x "scripts/diagnostics.py" ] || check "Diagnostic script executable" 1
else
    warn "Diagnostic script not found"
fi

if [ -f "backend/app/main.py" ]; then
    check "Main application exists" 0
else
    warn "Main application not found"
fi

# 6. Check logs directory
echo ""
echo "--- Logs & Data ---"
if [ -d "logs" ] || [ -d "/var/log/ai-f" ]; then
    check "Logs directory exists" 0
else
    warn "No logs directory found"
fi

# 7. Check certificates
echo ""
echo "--- Security ---"
if [ -d "certs" ]; then
    if [ -f "certs/server.crt" ] && [ -f "certs/server.key" ]; then
        check "TLS certificates present" 0
    else
        warn "TLS certificates missing (self-signed will be generated on startup)"
    fi
else
    warn "Certs directory not found"
fi

# Summary
echo ""
echo "=========================================="
echo "Summary: $PASS passed, $FAIL failed, $WARN warnings"
echo "=========================================="

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}System appears healthy!${NC}"
    exit 0
else
    echo -e "${RED}Found $FAIL critical issue(s). Please review.${NC}"
    exit 1
fi
