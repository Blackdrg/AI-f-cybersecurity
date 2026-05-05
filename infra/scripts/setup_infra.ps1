# AI-F Infrastructure Setup Script
# PowerShell script for Windows development environment
# Installs and configures PostgreSQL 15 + pgvector, Redis 7, and all dependencies

param(
    [string]$Action = "install",
    [switch]$WithMockModels = $false
)

$ErrorActionPreference = "Stop"

function Write-Header($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

function Test-Command($cmd) {
    return Get-Command $cmd -ErrorAction SilentlyContinue
}

function Wait-ForService($url, $timeout = 120) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $timeout) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return $true }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

Write-Header "Starting AI-F Infrastructure Setup"

# Check prerequisites
Write-Header "Checking Prerequisites"
if (-not (Test-Command "docker")) {
    Write-Error "Docker is not installed. Please install Docker Desktop for Windows."
    exit 1
}
if (-not (Test-Command "docker-compose")) {
    Write-Error "Docker Compose is not installed."
    exit 1
}

Write-Host "Docker is available" -ForegroundColor Green

# Create necessary directories
Write-Header "Creating directories"
$dirs = @(
    "D:\AI-F\AI-f\backend\models\onnx_bundle",
    "D:\AI-F\AI-f\backend\data",
    "D:\AI-F\AI-f\backend\logs",
    "D:\AI-F\AI-f\backend\data\uploads"
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created: $dir"
    }
}

# Copy environment file
Write-Header "Configuring environment"
$envFile = "D:\AI-F\AI-f\.env"
$infraEnv = "D:\AI-F\AI-f\infra\.env"
if (Test-Path $infraEnv) {
    Copy-Item $infraEnv $envFile -Force
    Write-Host "Environment file configured" -ForegroundColor Green
}

# Start infrastructure services
Write-Header "Starting Infrastructure Services"
Push-Location "D:\AI-F\AI-f\infra"

Write-Host "Starting PostgreSQL 15 + pgvector..." -NoNewline
docker-compose up -d postgres
if ($LASTEXITCODE -eq 0) { Write-Host " OK" -ForegroundColor Green }

Write-Host "Starting Redis 7 cluster..." -NoNewline
docker-compose up -d redis-master redis-replica
if ($LASTEXITCODE -eq 0) { Write-Host " OK" -ForegroundColor Green }

Write-Host "Waiting for services to be ready..." -NoNewline
Start-Sleep -Seconds 15

# Check PostgreSQL health
Write-Host "Checking PostgreSQL..." -NoNewline
$pingResult = docker exec ai-f-postgres-1 pg_isready -U postgres 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED (waiting...)" -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

# Check Redis health
Write-Host "Checking Redis..." -NoNewline
$redisResult = docker exec ai-f-redis-master-1 redis-cli ping
if ($redisResult -match "PONG") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
}

Pop-Location

# Install MaxMind GeoIP2 database (optional)
Write-Header "GeoIP Database"
$geoipPath = "D:\AI-F\AI-f\backend\data\GeoLite2-City.mmdb"
if (-not (Test-Path $geoipPath)) {
    Write-Host "GeoIP database not found. Download from https://dev.maxmind.com/geoip/geolite2-free-geolocation-data"
    Write-Host "Place GeoLite2-City.mmdb in: $geoipPath"
} else {
    Write-Host "GeoIP database found" -ForegroundColor Green
}

# Create mock ONNX models if requested
if ($WithMockModels) {
    Write-Header "Creating Mock ONNX Models"
    D:\AI-F\AI-f\backend\scripts\export_onnx.py 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Mock models created" -ForegroundColor Green
    } else {
        Write-Host "Using existing models or fallback to mock mode" -ForegroundColor Yellow
    }
}

# Summary
Write-Header "Setup Complete"
Write-Host @"
Infrastructure Status:
  - PostgreSQL 15 + pgvector: Running on port 5432
  - Redis 7 Master: Running on port 6379
  - Redis 7 Replica: Running on port 6380

Next Steps:
  1. Add your API keys to infra\.env
  2. Download GeoIP database (optional)
  3. Run: docker-compose up -d backend ui
  4. Run: pytest backend/tests/

To start the backend:
  cd infra
  docker-compose up -d backend

To run tests:
  pytest backend/tests/ -v --tb=short
"@ -ForegroundColor White

Write-Host "`nInfrastructure setup complete!" -ForegroundColor Green