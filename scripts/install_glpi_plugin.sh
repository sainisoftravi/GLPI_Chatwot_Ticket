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

# 2. If a download URL is provided, download and extract it directly
if [ -n "$PLUGIN_URL" ]; then
    echo "Downloading and installing plugin from: $PLUGIN_URL"
    FILENAME=$(basename "$PLUGIN_URL")
    
    # Download inside container
    docker exec -u 0 glpi-app bash -c "
        cd /var/www/glpi/plugins
        curl -sL '$PLUGIN_URL' -o '$FILENAME'
        if [[ '$FILENAME' == *.tar.gz ]] || [[ '$FILENAME' == *.tgz ]]; then
            tar -xzf '$FILENAME'
            rm -f '$FILENAME'
        elif [[ '$FILENAME' == *.zip ]]; then
            apt-get update -qq && apt-get install -y -qq unzip
            unzip -q -o '$FILENAME'
            rm -f '$FILENAME'
        fi
        chown -R www-data:www-data /var/www/glpi/plugins
        chmod -R 775 /var/www/glpi/plugins
    "
    echo "✅ Plugin extracted successfully into /var/www/glpi/plugins!"
fi

echo ""
echo "Installed plugins in GLPI:"
docker exec glpi-app ls -l /var/www/glpi/plugins

echo ""
echo "=========================================================="
echo " Now open GLPI: Setup > Plugins (or Setup > Marketplace)"
echo " Click 'Install' and 'Enable' on your new plugin."
echo "=========================================================="

