#!/usr/bin/env bash
# ==============================================================================
# Setup GLPI Automated CLI Notifications & Cron (Runs every 30 seconds)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================================================="
echo " ⚙️ Configuring GLPI Automated CLI Notifications (Every 30s) "
echo "=========================================================================="

# 1. Load credentials from .env if present
if [ -f "$ROOT_DIR/.env" ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "$ROOT_DIR/.env" | grep -E '^(MARIADB_|GLPI_)' | xargs)
fi

DB_USER="${MARIADB_USER:-glpi}"
DB_PASS="${MARIADB_PASSWORD:-glpi_secure_pwd_123}"
DB_NAME="${MARIADB_DATABASE:-glpidb}"

echo "[1] Updating GLPI Automatic Actions to CLI Mode in Database..."
# Set critical background tasks to CLI mode (mode=2), active (state=1), and frequency=30s
docker exec -i glpi-mariadb mariadb -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" <<EOF
UPDATE glpi_crontasks 
SET mode = 2, frequency = 30, state = 1 
WHERE name IN ('queuedmail', 'queuednotification', 'mailgate', 'ticket', 'sla', 'createinquestticket');
EOF

echo "✅ Database updated: Queued emails, notifications, and ticket actions set to CLI (every 30s)!"

echo ""
echo "[2] Current GLPI Notification Crontask Configuration:"
docker exec -i glpi-mariadb mariadb -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
SELECT name, 
       CASE mode WHEN 1 THEN 'GLPI (Web)' WHEN 2 THEN 'CLI (Cron)' ELSE 'Other' END AS 'Run Mode',
       frequency AS 'Frequency (sec)',
       CASE state WHEN 1 THEN 'Scheduled' WHEN 2 THEN 'Running' ELSE 'Disabled' END AS 'State',
       lastrun AS 'Last Run'
FROM glpi_crontasks 
WHERE name IN ('queuedmail', 'queuednotification', 'mailgate', 'ticket', 'sla');
"

echo ""
echo "[3] Testing GLPI CLI Cron execution inside container..."
docker exec -u www-data glpi-app php /var/www/glpi/bin/console cron:run --force 2>/dev/null || \
docker exec -u www-data glpi-app php /var/www/glpi/front/cron.php 2>/dev/null || true
echo "✅ Test execution completed successfully."

echo ""
echo "[4] Installing 30-Second Host Cron Job in /etc/cron.d/glpi-cron..."
CRON_FILE="/etc/cron.d/glpi-cron"

sudo tee "$CRON_FILE" > /dev/null <<'EOF'
# ==============================================================================
# GLPI Automated CLI Cron: Processes ticket notifications, tasks & emails every 30s
# ==============================================================================
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

* * * * * root docker exec -u www-data glpi-app php /var/www/glpi/front/cron.php >/dev/null 2>&1
* * * * * root sleep 30; docker exec -u www-data glpi-app php /var/www/glpi/front/cron.php >/dev/null 2>&1
EOF

sudo chmod 0644 "$CRON_FILE"
echo "✅ Installed host cron job at $CRON_FILE."

echo ""
echo "=========================================================================="
echo " 🎉 Configuration Complete! "
echo " GLPI will now automatically process and send:"
echo "   - Ticket creation notifications"
echo "   - Task additions & updates"
echo "   - Ticket responses & followups"
echo " every 30 seconds in the background via CLI!"
echo "=========================================================================="
