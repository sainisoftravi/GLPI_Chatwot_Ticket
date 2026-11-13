# ⏱️ GLPI Automated Notifications & 30-Second CLI Scheduler

By default, GLPI runs scheduled background tasks in **"GLPI (Internal)" mode**. In this mode, tasks are only triggered when a user actively clicks around in the web browser. If no one is browsing GLPI, no notifications or queued emails are sent!

To ensure that **all ticket creation, task assignment, and ticket response notifications are processed and sent automatically every 30 seconds**, we switch GLPI background tasks to **CLI (Command Line Interface)** mode and configure a background runner.

---

## 🚀 1-Command Automated Setup

Run this single command on your server terminal (`/home/ubuntu/Ticket_Managment_System_Webserver`):

```bash
cd /home/ubuntu/Ticket_Managment_System_Webserver
git pull origin main
chmod +x scripts/setup_glpi_cron_30s.sh
sudo ./scripts/setup_glpi_cron_30s.sh
```

### What this script does automatically:
1. **Switches Critical Crontasks to CLI Mode in the Database**:
   - `queuedmail` / `queuednotification`: Sends all pending email notifications.
   - `mailgate`: Checks and imports incoming emails into tickets.
   - `ticket`: Processes automatic ticket escalations and state changes.
   - `sla`: Monitors and computes SLA timers.
2. **Sets Execution Frequency to 30 Seconds**.
3. **Installs a 30-second System Cron Runner** in `/etc/cron.d/glpi-cron` that executes:
   ```cron
   * * * * * root docker exec -u www-data glpi-app php /var/www/glpi/front/cron.php >/dev/null 2>&1
   * * * * * root sleep 30; docker exec -u www-data glpi-app php /var/www/glpi/front/cron.php >/dev/null 2>&1
   ```

---

## 📧 Configuring GLPI Email Notifications (Web UI)

For GLPI to send emails (SMTP/PHP), ensure your email settings are configured:

1. Log in to GLPI: `http://<SERVER_IP>:8085`
2. Navigate to **Setup** > **Notifications**:
   - Set **Enable notifications** to **Yes**.
3. Click on **Email followups configuration**:
   - **Administrator email**: e.g., `it-support@yourdomain.com`
   - **Administrator name**: e.g., `IT Helpdesk`
   - **Way of sending emails**: Select **SMTP** (or PHP mail).
   - Enter your SMTP Host (e.g., `smtp.gmail.com`, `smtp.office365.com`, or local SMTP), Port, Username, and Password.
   - Click **Send a test email to the administrator** to verify connectivity.
4. Click **Save**.

---

## 🔍 How to Verify in GLPI Web Interface

1. Go to **Setup** > **Automatic actions** (`http://<SERVER_IP>:8085/front/crontask.php`).
2. Look for **`queuedmail`** (or **`queuednotification`**):
   - **Run mode**: `CLI`
   - **Run frequency**: `30 seconds` or `1 minute`
   - **Status**: `Scheduled`
   - **Last run**: Updates every 30 seconds!

---

## 📱 WhatsApp Real-Time Notifications

While emails go through GLPI's queued notification system:
- **WhatsApp Ticket Confirmations**: Dispatched instantly by the **Integration Bridge** (`http://bridge:5000/webhook/openwa`) the moment a `#ticket` is created.
- **WhatsApp Status Updates**: When a technician solves or updates a ticket, GLPI's native webhook (`Setup > Webhooks` pointing to `http://bridge:5000/webhook/glpi`) triggers an immediate WhatsApp update back to the customer's phone.

