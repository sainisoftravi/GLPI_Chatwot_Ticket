#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " IT Ticket & Task Management + Chatwoot WhatsApp AI Setup "
echo "=========================================================="

if [ ! -f .env ]; then
    echo "[1/4] Creating .env from .env.example..."
    cp .env.example .env
fi

echo "[2/4] Verifying Docker..."
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

echo "[3/4] Initializing Chatwoot Database..."
$COMPOSE_CMD run --rm chatwoot-web bundle exec rails db:chatwoot_prepare

echo "[4/4] Starting all containers..."
$COMPOSE_CMD up -d --build

echo "=========================================================="
echo " All services running!"
echo " - GLPI ITSM:           http://localhost:8085"
echo " - Chatwoot Live & WA:  http://localhost:8050"
echo " - Integration Bridge:  http://localhost:5050/health"
echo "=========================================================="

