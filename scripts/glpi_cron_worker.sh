#!/usr/bin/env bash
# ==============================================================================
# GLPI Automated Cron & Notification Dispatcher (Runs every 30s)
# Runs continuously as www-data to process email notifications, tickets & alerts
# ==============================================================================

echo "=========================================================================="
echo " ⏱️ Starting GLPI 30-Second Notification & Cron Worker"
echo "=========================================================================="

# Wait for GLPI application & Database to be reachable
sleep 10

echo "✅ GLPI Cron Worker active. Monitoring queue every 30 seconds..."

while true; do
    echo "--- [$(date '+%Y-%m-%d %H:%M:%S')] Running GLPI Cron Cycle ---"
    
    # 1. Update Database:
    # - Ensure delay_send_emails = 0 (instant delivery, no holding)
    # - Ensure queuednotification, queuedmail, mailgate, ticket, sla are in CLI mode (mode=2), active (state=1), 30s
    # - Reset any stuck 'running' tasks (state=2 -> state=1)
    php -r '
        try {
            $h = getenv("GLPI_DB_HOST") ?: "glpi-db";
            $d = getenv("GLPI_DB_NAME") ?: "glpidb";
            $u = getenv("GLPI_DB_USER") ?: "glpi";
            $p = getenv("GLPI_DB_PASSWORD") ?: "glpi_secure_pwd_123";
            $pdo = new PDO("mysql:host=$h;dbname=$d", $u, $p, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
            
            // Set 0 delay for all entities (send immediately, do not hold in queue)
            $pdo->exec("UPDATE glpi_entities SET delay_send_emails = 0 WHERE delay_send_emails != 0");
            
            // Set critical tasks to CLI mode (mode=2), active (state=1), frequency=30
            $pdo->exec("UPDATE glpi_crontasks SET mode = 2, frequency = 30, state = 1 WHERE name IN (\"queuednotification\", \"queuedmail\", \"mailgate\", \"ticket\", \"sla\")");
            
            // Reset any task stuck in running state (state=2)
            $pdo->exec("UPDATE glpi_crontasks SET state = 1 WHERE state = 2");
        } catch (Exception $e) {
            echo "DB Config Note: " . $e->getMessage() . "\n";
        }
    '

    # 2. Specifically force queuednotification to flush the email queue immediately
    php /var/www/glpi/front/cron.php --force queuednotification || true

    # 3. Process other pending scheduled actions
    php /var/www/glpi/front/cron.php 10 || true

    # 4. Sleep 30 seconds
    sleep 30
done
