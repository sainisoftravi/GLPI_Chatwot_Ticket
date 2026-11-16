#!/usr/bin/env bash
# ==============================================================================
# GLPI Automated Cron & Notification Dispatcher (Runs every 30s)
# Runs continuously to process email notifications, tickets & alerts
# ==============================================================================

echo "=========================================================================="
echo " ⏱️ Starting GLPI 30-Second Notification & Cron Worker"
echo "=========================================================================="

# Wait for GLPI application & Database to be reachable
sleep 5

echo "✅ GLPI Cron Worker active. Monitoring queue every 30 seconds..."

while true; do
    echo "--- [$(date '+%Y-%m-%d %H:%M:%S')] Running GLPI Cron Cycle ---"
    
    # 1. Update Database using mysqli (native GLPI driver)
    php -r '
        $h = getenv("GLPI_DB_HOST") ?: "glpi-db";
        $d = getenv("GLPI_DB_NAME") ?: "glpidb";
        $u = getenv("GLPI_DB_USER") ?: "glpi";
        $p = getenv("GLPI_DB_PASSWORD") ?: "glpi_secure_pwd_123";
        $m = @new mysqli($h, $u, $p, $d);
        if (!$m->connect_error) {
            $m->query("UPDATE glpi_entities SET delay_send_emails = 0 WHERE delay_send_emails != 0");
            $m->query("UPDATE glpi_crontasks SET mode = 2, frequency = 30, state = 1 WHERE name IN (\"queuednotification\", \"queuedmail\", \"mailgate\", \"ticket\", \"sla\")");
            $m->query("UPDATE glpi_crontasks SET state = 1 WHERE state = 2");
            $m->close();
        }
    '

    # 2. Specifically force queuednotification with verbose output
    php -d display_errors=on /var/www/glpi/front/cron.php --debug --force queuednotification || true

    # 3. Process other pending scheduled actions
    php /var/www/glpi/front/cron.php 5 || true

    # 4. Sleep 30 seconds
    sleep 30
done
