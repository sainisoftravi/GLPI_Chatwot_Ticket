# IT Ticketing & WhatsApp AI System Setup Script (Windows PowerShell)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " IT Ticket & Task Management + Chatwoot WhatsApp AI Setup " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Step 1: Check .env file
if (-not (Test-Path ".env")) {
    Write-Host "[1/4] Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env file. Please review and update passwords or tokens when ready." -ForegroundColor Green
} else {
    Write-Host "[1/4] .env file already exists." -ForegroundColor Green
}

# Step 2: Verify Docker status
Write-Host "[2/4] Verifying Docker Engine..." -ForegroundColor Yellow
try {
    $dockerCheck = docker ps 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Docker Engine does not appear to be running." -ForegroundColor Red
        Write-Host "Please start Docker Desktop on your machine and re-run this script." -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "Error connecting to Docker. Ensure Docker Desktop is started." -ForegroundColor Red
    exit 1
}

# Step 3: Initialize Chatwoot Database (First time run)
Write-Host "[3/4] Initializing Chatwoot Database schemas..." -ForegroundColor Yellow
docker-compose run --rm chatwoot-web bundle exec rails db:chatwoot_prepare

# Step 4: Start all services in detached mode
Write-Host "[4/4] Starting GLPI, Chatwoot, and Bridge containers..." -ForegroundColor Yellow
docker-compose up -d --build

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " Stack Deployed Successfully! " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " Access Endpoints:" -ForegroundColor Cyan
Write-Host " - GLPI ITSM Portal:      http://localhost:8085"
Write-Host " - Chatwoot Live & WA:    http://localhost:8050"
Write-Host " - OpenWA Dashboard (QR): http://localhost:2785"
Write-Host " - Integration Bridge:    http://localhost:5050/health"
Write-Host "==========================================================" -ForegroundColor Green

