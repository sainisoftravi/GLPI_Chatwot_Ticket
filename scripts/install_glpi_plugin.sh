#!/usr/bin/env bash
# ==============================================================================
# GLPI Plugin Installer & Permission Fixer Helper
# ==============================================================================

set -e

PLUGIN_URL="$1"

echo "=========================================================="
echo " 🔌 GLPI Plugin Manager "
echo "=========================================================="

# 1. Ensure write permissions for GLPI web server (www-data)
echo "Setting write permissions on plugins & marketplace directories..."
docker exec -u 0 glpi-app chown -R www-data:www-data /var/www/glpi/plugins /var/www/glpi/marketplace 2>/dev/null || true
docker exec -u 0 glpi-app chmod -R 775 /var/www/glpi/plugins /var/www/glpi/marketplace 2>/dev/null || true

# 2. If an existing archive exists in the folder or a URL is passed, extract it
docker exec -u 0 glpi-app bash -c "
    apt-get update -qq && apt-get install -y -qq bzip2 tar unzip curl >/dev/null 2>&1 || true
    cd /var/www/glpi/plugins

    # Download if URL provided
    if [ -n '$PLUGIN_URL' ]; then
        FILENAME=\$(basename '$PLUGIN_URL')
        echo \"Downloading: \$FILENAME ...\"
        curl -sL '$PLUGIN_URL' -o \"\$FILENAME\"
    fi

    # Extract all pending archives in /var/www/glpi/plugins
    for f in *.tar.bz2 *.tbz2 *.bz2; do
        [ -e \"\$f\" ] || continue
        echo \"Extracting bzip2 archive: \$f ...\"
        tar -xjf \"\$f\"
        rm -f \"\$f\"
    done

    for f in *.tar.gz *.tgz; do
        [ -e \"\$f\" ] || continue
        echo \"Extracting gzip archive: \$f ...\"
        tar -xzf \"\$f\"
        rm -f \"\$f\"
    done

    for f in *.zip; do
        [ -e \"\$f\" ] || continue
        echo \"Extracting zip archive: \$f ...\"
        unzip -q -o \"\$f\"
        rm -f \"\$f\"
    done

    chown -R www-data:www-data /var/www/glpi/plugins /var/www/glpi/marketplace
    chmod -R 775 /var/www/glpi/plugins /var/www/glpi/marketplace
"

echo ""
echo "Installed plugin folders in GLPI (/var/www/glpi/plugins):"
docker exec glpi-app ls -la /var/www/glpi/plugins

echo ""
echo "=========================================================="
echo " Now refresh GLPI: Setup > Plugins (or Setup > Marketplace)"
echo " You will see the extracted plugins ready to Install & Enable!"
echo "=========================================================="
