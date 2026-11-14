#!/usr/bin/env bash
# ==============================================================================
# GLPI 30-Second Background Cron & Notification Dispatcher
# Runs permanently inside glpi-cron container to process emails, tickets & alerts
# ==============================================================================

echo "=========================================================================="
echo " ⏱️ Starting GLPI 30-Second Automated Notification Worker"
echo "=========================================================================="

# Wait for database and GLPI core to be ready
sleep 15

echo "✅ GLPI Cron Worker active. Processing background tasks every 30 seconds..."

while true; do
    # 1. Ensure queued notification and ticket tasks are in CLI mode (mode=2), active (state=1), 30s
    php -r '
        try {
            $h = getenv("GLPI_DB_HOST") ?: "glpi-db";
            $d = getenv("GLPI_DB_NAME") ?: "glpidb";
            $u = getenv("GLPI_DB_USER") ?: "glpi";
            $p = getenv("GLPI_DB_PASSWORD") ?: "glpi_secure_pwd_123";
            $pdo = new PDO("mysql:host=$h;dbname=$d", $u, $p);
            $pdo->exec("UPDATE glpi_crontasks SET mode = 2, frequency = 30, state = 1 WHERE name IN (\"queuednotification\", \"queuedmail\", \"mailgate\", \"ticket\", \"sla\")");
        } catch (Exception $e) {}
    '

    # 2. Execute GLPI cron to process queued emails, tickets, and followups
    su -s /bin/bash www-data -c "php /var/www/glpi/front/cron.php" >/dev/null 2>&1 || true

    # 3. Sleep 30 seconds
    sleep 30
done
