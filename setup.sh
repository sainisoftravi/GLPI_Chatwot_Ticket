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
docker-compose --version

echo "[3/4] Initializing Chatwoot Database..."
docker-compose run --rm chatwoot-web bundle exec rails db:chatwoot_prepare

echo "[4/4] Starting all containers..."
docker-compose up -d --build

echo "=========================================================="
echo " All services running!"
echo " - GLPI ITSM:           http://localhost:8080"
echo " - Chatwoot Live & WA:  http://localhost:3000"
echo " - Integration Bridge:  http://localhost:5000/health"
echo "=========================================================="
