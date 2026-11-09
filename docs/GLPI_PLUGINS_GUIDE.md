# 🔌 GLPI Plugin Installation Guide

In Docker containers, GLPI plugins fail to install or disappear after container restarts due to two reasons:
1. **Directory Permissions**: The `/var/www/glpi/plugins` and `/var/www/glpi/marketplace` directories inside the container are owned by `root`, preventing the GLPI web process (`www-data`) from downloading or creating files.
2. **Missing Persistence**: By default, `/var/www/glpi/plugins` is ephemeral unless mapped to a Docker volume.

We have updated `docker-compose.yml` to persist both `glpi_plugins` and `glpi_marketplace` volumes.

---

## ⚡ Method 1: Fix Web UI Permissions (Install via Browser Marketplace)

To enable 1-click plugin installation from the GLPI Web Marketplace:

Run this command on your server terminal:
```bash
docker exec -u 0 glpi-app chown -R www-data:www-data /var/www/glpi/plugins /var/www/glpi/marketplace
docker exec -u 0 glpi-app chmod -R 775 /var/www/glpi/plugins /var/www/glpi/marketplace
```

Now in your browser:
1. Open GLPI: `http://<SERVER_IP>:8085`
2. Go to **Setup** > **Marketplace** (or **Setup** > **Plugins**).
3. The directory write error is gone, and you can click **Install** directly on any plugin!

---

## ⚡ Method 2: Install via 1-Command Helper Script

You can install any plugin by URL using the helper script:

```bash
cd /home/ubuntu/Ticket_Managment_System_Webserver
chmod +x scripts/install_glpi_plugin.sh

# Example 1: Install the Webhook Plugin (for WhatsApp status callbacks)
./scripts/install_glpi_plugin.sh https://github.com/pluginsGLPI/webhook/releases/download/1.2.0/glpi-webhook-1.2.0.tar.gz

# Example 2: Install Formcreator (Custom user ticket forms)
./scripts/install_glpi_plugin.sh https://github.com/pluginsGLPI/formcreator/releases/download/2.13.8/glpi-formcreator-2.13.8.tar.bz2
```

---

## ⚡ Method 3: Manual Direct Extraction

If you have a plugin `.tar.gz` or `.zip` file from the [GLPI Plugins Directory](https://plugins.glpi-project.org/):

```bash
# 1. Download or move the archive into the container plugins folder
docker exec -u 0 glpi-app bash -c "
cd /var/www/glpi/plugins
curl -sL <PLUGIN_DOWNLOAD_URL> -o plugin.tar.gz
tar -xzf plugin.tar.gz
rm -f plugin.tar.gz
chown -R www-data:www-data /var/www/glpi/plugins
chmod -R 775 /var/www/glpi/plugins
"
```

---

## 🚀 How to Enable Installed Plugins in GLPI

1. In GLPI (`http://<SERVER_IP>:8085`), navigate to **Setup** > **Plugins**.
2. Locate your plugin in the list.
3. Click the **Install** button (wrench/gear icon).
4. Click the **Enable** button (play/check icon).

The plugin is now active and its configuration menu will appear under **Setup** or **Administration**.
