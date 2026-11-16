#!/usr/bin/env bash
# ==============================================================================
# Complete IT Ticket & Task Management + Chatwoot WhatsApp AI Automated Setup
# Works on any deployment directory / server location
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo " IT Ticket & Task Management + Chatwoot WhatsApp AI Setup "
echo " Target Directory: $SCRIPT_DIR"
echo "=========================================================="

# 1. Environment file check
if [ ! -f .env ]; then
    echo "[1/6] Creating .env from .env.example..."
    cp .env.example .env
fi

# 2. Make all helper scripts executable
echo "[2/6] Setting executable permissions on helper scripts..."
chmod +x scripts/*.sh setup.sh 2>/dev/null || true

# 3. Docker Compose detection
echo "[3/6] Verifying Docker environment..."
docker --version

if docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "Error: Docker Compose is not installed."
    exit 1
fi
echo "Using compose command: $COMPOSE_CMD"

# 4. Prepare Chatwoot Database
echo "[4/6] Initializing Chatwoot Database..."
$COMPOSE_CMD run --rm chatwoot-web bundle exec rails db:chatwoot_prepare || true

# 5. Build and launch all stack containers (including glpi-cron)
echo "[5/6] Starting all containers..."
$COMPOSE_CMD up -d --build --remove-orphans

echo "Waiting 15 seconds for GLPI and MariaDB to initialize..."
sleep 15

# 6. Configure automated 30s notifications and queue flush
echo "[6/6] Configuring GLPI 30-Second Notification Cron..."
./scripts/setup_glpi_cron_30s.sh || true

echo "=========================================================="
echo " All services running!"
echo " - GLPI ITSM:           http://localhost:8085"
echo " - Chatwoot Live & WA:  http://localhost:8050"
echo " - OpenWA Dashboard(QR):http://localhost:2785"
echo " - Integration Bridge:  http://localhost:5050/health"
echo " - GLPI 30s Auto Cron:  glpi-cron container active"
echo "=========================================================="
