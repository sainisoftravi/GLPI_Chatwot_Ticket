#!/usr/bin/env bash
# ==============================================================================
# Setup GLPI Automated CLI Notifications & Cron (Runs anywhere dynamically)
# ==============================================================================
set -e

# Detect deployment root dynamically (works on any directory path / server location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================================================="
echo " ⚙️ Configuring GLPI Automated CLI Notifications (Every 30s) "
echo " Target Deployment Directory: $ROOT_DIR"
echo "=========================================================================="

cd "$ROOT_DIR"

# 1. Load credentials from .env if present
if [ -f "$ROOT_DIR/.env" ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "$ROOT_DIR/.env" | grep -E '^(MARIADB_|GLPI_)' | xargs)
fi

DB_USER="${MARIADB_USER:-glpi}"
DB_PASS="${MARIADB_PASSWORD:-glpi_secure_pwd_123}"
DB_NAME="${MARIADB_DATABASE:-glpidb}"

# 2. Ensure scripts have execution permissions
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true

# 3. Check if glpi-mariadb container is running
echo "[1/4] Checking Database Connectivity..."
if ! docker ps --format '{{.Names}}' | grep -q "glpi-mariadb"; then
    echo "⚠️ glpi-mariadb container is not running yet. Starting database..."
    docker compose up -d glpi-db
    sleep 5
fi

# 4. Update GLPI database: 0-minute delay and CLI mode for all notification tasks
echo "[2/4] Updating GLPI Database (0-delay immediate delivery & CLI mode)..."
docker exec -i glpi-mariadb mariadb -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" <<EOF
-- Set immediate delivery (0 delay) for all entities
UPDATE glpi_entities SET delay_send_emails = 0 WHERE delay_send_emails != 0;

-- Set critical tasks to CLI mode (mode=2), active (state=1), and frequency=30s
UPDATE glpi_crontasks 
SET mode = 2, frequency = 30, state = 1 
WHERE name IN ('queuedmail', 'queuednotification', 'mailgate', 'ticket', 'sla', 'createinquestticket');

-- Reset any task stuck in running state
UPDATE glpi_crontasks SET state = 1 WHERE state = 2;
EOF

echo "✅ Database updated: delay_send_emails=0 and tasks set to CLI mode (30s)!"

# 5. Launch / Restart glpi-cron background container
echo "[3/4] Ensuring glpi-cron container is active..."
docker compose up -d glpi-cron

# 6. Force immediate flush of pending notification queue
echo "[4/4] Forcing immediate queue flush inside glpi-app..."
docker exec -u www-data glpi-app php /var/www/glpi/front/cron.php --force queuednotification || true
docker exec -u www-data glpi-app php /var/www/glpi/front/cron.php 10 || true

echo ""
echo "Current Pending Email Queue Count:"
docker exec -i glpi-mariadb mariadb -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT count(*) AS 'Pending Emails In Queue' FROM glpi_queuednotifications;
"

echo "=========================================================================="
echo " 🎉 Automated Cron Deployment Complete! "
echo " The glpi-cron container is running permanently in the background."
echo " Every ticket, task, or followup will now notify automatically every 30s."
echo "=========================================================================="
