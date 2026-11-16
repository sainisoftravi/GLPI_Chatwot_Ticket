#!/usr/bin/env bash
# ==============================================================================
# GLPI Automated Cron & Notification Dispatcher (Runs every 30s)
# Runs continuously to process email notifications, tickets & alerts
# ==============================================================================

echo "=========================================================================="
echo " ⏱️ Starting GLPI 30-Second Notification & Cron Worker"
echo "=========================================================================="

# Wait for GLPI application to be reachable
sleep 5

echo "✅ GLPI Cron Worker active. Monitoring queue every 30 seconds..."

while true; do
    echo "--- [$(date '+%Y-%m-%d %H:%M:%S')] Running GLPI Cron Cycle ---"
    
    # 1. Specifically force queuednotification to flush the email queue immediately
    php /var/www/glpi/front/cron.php --force queuednotification || true

    # 2. Process other pending scheduled actions
    php /var/www/glpi/front/cron.php 5 || true

    # 3. Sleep 30 seconds
    sleep 30
done
