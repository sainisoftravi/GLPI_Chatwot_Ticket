# 🛠️ Complete Installation & Setup Guide

This guide walks you through deploying the **IT Ticket & Task Management System** on your server from scratch.

---

## 📋 System Requirements

- **Operating System:** Ubuntu 22.04 / 24.04 LTS, Debian 12, or macOS / Windows with Docker Desktop.
- **CPU Architecture:** Native support for both **ARM64** (AWS Graviton, Apple Silicon, Ampere) and **AMD64** (x86_64).
- **RAM:** Minimum 4 GB recommended (Chatwoot Rails, Sidekiq, GLPI, and OpenWA Baileys).
- **Ports Required:**
  - `8085`: GLPI ITSM & Task Kanban
  - `8050`: Chatwoot Live Chat & Omnichannel Hub
  - `2785`: OpenWA WhatsApp Gateway & QR Dashboard
  - `5050`: Integration Bridge Webhook

---

## 🚀 Step 1: Clone or Copy Files to Server

On your server terminal:

```bash
# 1. Create target deployment directory
mkdir -p /home/ubuntu/Ticket_Managment_System_Webserver
cd /home/ubuntu/Ticket_Managment_System_Webserver

# 2. Clone the repository
git clone https://github.com/sainisoftravi/GLPI_Chatwot_Ticket.git .
```

---

## ⚙️ Step 2: Environment Configuration

Copy the template to your live `.env` file:

```bash
cp .env.example .env
```

Review your `.env` configuration (default ports are already conflict-free):
```ini
GLPI_PORT=8085
CHATWOOT_PORT=8050
OPENWA_PORT=2785
BRIDGE_PORT=5050

# Database Passwords (customize if desired)
MARIADB_ROOT_PASSWORD=glpi_root_secure_pwd_123
MARIADB_PASSWORD=glpi_secure_pwd_123
POSTGRES_PASSWORD=chatwoot_secure_pwd_123
```

---

## 🐳 Step 3: Initialize Database & Start Containers

Run the automated setup script or execute manually:

### Option A: Using the Automated Script
```bash
chmod +x setup.sh
./setup.sh
```

### Option B: Manual Docker Compose Commands
```bash
# 1. Prepare Chatwoot PostgreSQL database schema (first time only)
docker compose run --rm chatwoot-web bundle exec rails db:chatwoot_prepare

# 2. Build and launch all 8 services
docker compose up -d --build

# 3. Verify container status
docker compose ps
```

You should see all containers running:
- `glpi-app`
- `glpi-mariadb`
- `chatwoot-web`
- `chatwoot-worker`
- `chatwoot-postgres`
- `chatwoot-redis`
- `openwa-gateway`
- `it-integration-bridge`

---

## 📱 Step 4: Connect WhatsApp via OpenWA (Free QR Link)

1. **Get the Auto-Generated OpenWA Admin API Key**:
   ```bash
   docker exec openwa-gateway cat /app/data/.api-key
   ```
   Copy the key string printed to your terminal.

2. **Add to `.env`**:
   ```bash
   nano .env
   # Set: OPENWA_API_KEY=your_copied_key_here
   ```
   Restart the bridge container:
   ```bash
   docker compose restart bridge
   ```

3. **Scan WhatsApp QR Code**:
   - Open in your browser: `http://<SERVER_IP>:2785`
   - Sign in using your `OPENWA_API_KEY`.
   - Click **Create Session**:
     - Name: `it-support`
     - Engine: `baileys`
     - Click **Start Session**.
   - Click **Scan QR Code**.
   - Open WhatsApp on your mobile phone: **Linked Devices > Link a Device** and scan the screen.

4. **Add Bridge Webhook in OpenWA**:
   - In OpenWA Dashboard, go to **Webhooks > Add Webhook**:
     - **URL**: `http://bridge:5000/webhook/openwa`
     - **Event**: `message.received`
     - Click **Save**.

---

## 💬 Step 5: Configure Chatwoot

1. **Initial Admin Setup**:
   - Open `http://<SERVER_IP>:8050` in your browser.
   - Enter your name, organization name, and admin credentials.

2. **Create API Channel Inbox for OpenWA**:
   - Go to **Settings > Inboxes > Add Inbox**.
   - Select **API Channel**.
   - **Channel Name**: `WhatsApp OpenWA`
   - **Webhook URL**: `http://bridge:5000/webhook/chatwoot`
   - Click **Create Channel**.
   - Confirm the created Inbox ID is `1` (matches `CHATWOOT_INBOX_ID=1` in `.env`).

3. **Get Chatwoot Access Token**:
   - Click on your profile avatar (bottom-left) > **Profile Settings**.
   - Scroll to **Access Token** and copy the string.
   - Add to `.env`:
     ```ini
     CHATWOOT_API_ACCESS_TOKEN=your_chatwoot_token_here
     ```
   - Restart bridge:
     ```bash
     docker compose restart bridge
     ```

---

## 📋 Step 6: Configure GLPI ITSM & Task Kanban

1. **Access GLPI**:
   - Open `http://<SERVER_IP>:8085` in your browser.
   - Login with:
     - Username: `glpi`
     - Password: `glpi`
   - *Immediately go to **Administration > Users > glpi** to change your password.*

2. **Enable REST API**:
   - Go to **Setup > General > API** tab.
   - Set **Enable REST API** = `Yes`.
   - Set **Enable login with external token** = `Yes`.
   - Under **API clients**, click **Add API client**:
     - Name: `Chatwoot Bridge`
     - Active: `Yes`
     - Regenerate **Application token (app_token)** and copy it.

3. **Generate User Token**:
   - Go to **Administration > Users > glpi > API Token**.
   - Regenerate **Personal token (user_token)** and copy it.

4. **Update `.env`**:
   ```ini
   GLPI_APP_TOKEN=your_app_token_here
   GLPI_USER_TOKEN=your_user_token_here
   ```
   Restart bridge:
   ```bash
   docker compose restart bridge
   ```

5. **Access the Kanban Board**:
   - Go to **Assistance > Tickets**.
   - Change the view mode in the top right to **Kanban (Global)**.
   - You will see tickets organized in columns: `New`, `Assigned`, `Planned`, `Pending`, `Solved`.

---

## 🧪 Step 7: Testing the Complete Integration

From your server terminal:
```bash
python3 scripts/simulate_test.py
```

Or send a real WhatsApp message to your connected phone:
```text
Hello, our office internet is down. #ticket
```
- Open GLPI: You will see a new ticket created with an initial diagnostic task in Kanban!
- Open Chatwoot: You will see the conversation thread with the user and an internal technician note containing the GLPI ticket link!

---

## 🔧 Operational & Maintenance Commands

### View Service Logs
```bash
# View all logs in real time
docker compose logs -f

# View Bridge logs specifically
docker compose logs -f bridge

# View OpenWA logs
docker compose logs -f openwa
```

### Restart a Specific Container
```bash
docker compose restart <service_name>
```

### Pull Updates & Redeploy
```bash
git pull origin main
docker compose up -d --build
```

