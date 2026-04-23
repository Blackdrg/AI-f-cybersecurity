# LEVI-AI Enterprise One-Click Installer (Windows)
# Requires: PowerShell 5.1+, Docker Desktop, Git

Write-Host "--- LEVI-AI Enterprise Installation Started ---" -ForegroundColor Cyan

# 1. Check for Prerequisites
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (!$docker) {
    Write-Error "Docker not found. Please install Docker Desktop for Windows."
    exit
}

$git = Get-Command git -ErrorAction SilentlyContinue
if (!$git) {
    Write-Error "Git not found. Please install Git for Windows."
    exit
}

# 2. Clone Repository
if (!(Test-Path "AI-f")) {
    git clone https://github.com/Blackdrg/AI-f-cybersecurity.git AI-f
    Set-Location "AI-f"
}

# 3. Setup Environment
if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    $secret = [Convert]::ToBase64String((1..32 | ForEach-Object { [byte](Get-Random -Minimum 0 -Maximum 255) }))
    Add-Content ".env" "`nGENERIC_SECRET=$secret"
    Write-Host "Created .env with random secrets." -ForegroundColor Green
}

# 4. Start Services
Set-Location "infra"
docker-compose pull
docker-compose up -d

# 5. Verify
Write-Host "Waiting for services to stabilize (20s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method Get -ErrorAction Stop
    Write-Host "--- Installation Complete! ---" -ForegroundColor Green
    Write-Host "API Docs: http://localhost:8000/docs"
    Write-Host "Dashboard: http://localhost:3000"
} catch {
    Write-Error "Backend failed to start. Check logs with 'docker-compose logs backend'"
}
