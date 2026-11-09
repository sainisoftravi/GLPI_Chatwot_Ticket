# 📡 API Reference & Integration Protocol

This document covers all REST API endpoints, webhook formats, request/response schemas, and authentication headers used across **GLPI**, **Chatwoot**, **OpenWA**, and the **Integration Bridge**.

---

## 1. Integration Bridge Endpoints (`:5050`)

Base URL: `http://localhost:5050` (or `http://bridge:5000` inside Docker)

---

### `GET /health`
Checks the operational status of the Bridge service and its connections to GLPI, Chatwoot, and OpenWA.

#### Response:
```json
{
  "status": "healthy",
  "service": "glpi-chatwoot-openwa-bridge",
  "glpi_target": "http://glpi:80",
  "chatwoot_target": "http://chatwoot-web:3000",
  "openwa_target": "http://openwa:2785",
  "openwa_session": {
    "status": "connected",
    "name": "it-support"
  }
}
```

---

### `POST /webhook/openwa`
Receives incoming WhatsApp message events dispatched by the OpenWA Gateway.

#### Headers:
- `Content-Type: application/json`

#### Request Payload:
```json
{
  "event": "message.received",
  "data": {
    "chatId": "14155552671@c.us",
    "from": "14155552671@c.us",
    "fromMe": false,
    "notifyName": "Sarah Connor",
    "body": "My monitor is flickering and turning black. #ticket",
    "type": "chat",
    "timestamp": 1731145200
  }
}
```

#### Workflow Triggered:
1. Searches or creates a contact for `14155552671@c.us` in Chatwoot.
2. Creates or opens an active conversation in Chatwoot's API Channel.
3. If the message starts with `#ticket` or `/ticket`, creates an ITIL Ticket in GLPI with an initial Kanban sub-task.

---

### `POST /webhook/chatwoot`
Receives webhook events triggered by Chatwoot when agents or AI reply, or when conversation labels/statuses change.

#### Headers:
- `Content-Type: application/json`

#### Request Payload (Outgoing Message from Agent/AI):
```json
{
  "event": "message_created",
  "id": 8421,
  "content": "Please check if your HDMI cable is securely connected to the dock.",
  "message_type": "outgoing",
  "private": false,
  "conversation": {
    "id": 105,
    "labels": ["hardware-support"]
  },
  "meta": {
    "sender": {
      "phone_number": "+14155552671"
    }
  }
}
```

#### Workflow Triggered:
1. If `message_type == "outgoing"` and `private == false`, the bridge forwards the text to the recipient's WhatsApp via OpenWA.
2. If `message_created` contains `#ticket` or labels include `ticket-needed`, triggers GLPI ticket creation.

---

### `POST /webhook/glpi`
Receives notification events from GLPI when a technician updates or solves an ITIL ticket.

#### Request Payload:
```json
{
  "ticket_id": 101,
  "status": "Solved",
  "solution": "Replaced faulty DisplayPort cable. Display operating normally.",
  "chatwoot_conversation_id": 105,
  "phone_number": "+14155552671"
}
```

#### Workflow Triggered:
1. Sends the solution note to the customer's WhatsApp via OpenWA.
2. Updates the Chatwoot conversation thread with the technician's notes.

---

## 2. GLPI REST API Protocol (`/apirest.php`)

GLPI uses a two-token authentication model:
1. **`App-Token`**: Identifies the client application (`Chatwoot Bridge`).
2. **`Session-Token`**: Acquired dynamically using the technician's `user_token`.

---

### Step 1: Session Initialization
`GET http://glpi:80/apirest.php/initSession`

#### Headers:
```http
App-Token: <GLPI_APP_TOKEN>
Authorization: user_token <GLPI_USER_TOKEN>
```

#### Response:
```json
{
  "session_token": "a1b2c3d4e5f6g7h8i9j0"
}
```

---

### Step 2: Create ITIL Ticket
`POST http://glpi:80/apirest.php/Ticket`

#### Headers:
```http
App-Token: <GLPI_APP_TOKEN>
Session-Token: a1b2c3d4e5f6g7h8i9j0
Content-Type: application/json
```

#### Request Payload:
```json
{
  "input": {
    "name": "IT Request from Sarah Connor: Monitor is flickering...",
    "content": "<p>My monitor is flickering and turning black.</p><hr/><p><b>Requester:</b> Sarah Connor<br/><b>WhatsApp:</b> +14155552671</p>",
    "urgency": 3,
    "status": 1,
    "type": 1,
    "itilcategories_id": 1
  }
}
```

#### GLPI Status Codes:
- `1` = New (Unassigned)
- `2` = Assigned (In Processing)
- `3` = Planned
- `4` = Pending
- `5` = Solved
- `6` = Closed

#### Response:
```json
{
  "id": 101,
  "message": "Item successfully added: Ticket (101)"
}
```

---

### Step 3: Add Kanban Task to Ticket
`POST http://glpi:80/apirest.php/TicketTask`

#### Request Payload:
```json
{
  "input": {
    "tickets_id": 101,
    "content": "Initial Triage & Diagnostics (Auto-generated from WhatsApp AI Escalation)",
    "state": 1
  }
}
```
*Task states: `1` = To do, `2` = In progress, `3` = Done.*

---

## 3. OpenWA Gateway API Protocol (`:2785`)

Base URL: `http://openwa:2785/api`

---

### Send WhatsApp Message
`POST http://openwa:2785/api/sessions/{sessionName}/messages/send-text`

#### Headers:
```http
Content-Type: application/json
X-API-Key: <OPENWA_API_KEY>
```

#### Request Payload:
```json
{
  "chatId": "14155552671@c.us",
  "text": "🎫 Hello! Your request has been logged as IT Ticket #101. An IT technician is investigating."
}
```

#### Response:
```json
{
  "status": "success",
  "id": "true_14155552671@c.us_3EB0...",
  "timestamp": 1731145220
}
```

---

### Get Session Status
`GET http://openwa:2785/api/sessions/{sessionName}`

#### Headers:
```http
X-API-Key: <OPENWA_API_KEY>
```

#### Response:
```json
{
  "status": "connected",
  "name": "it-support",
  "engine": "baileys",
  "me": {
    "id": "19995551234@c.us",
    "name": "IT Support Desk"
  }
}
```

---

## 4. Chatwoot API Channel Protocol (`:3000`)

Base URL: `http://chatwoot-web:3000/api/v1/accounts/{account_id}`

---

### Search or Create Contact
`GET http://chatwoot-web:3000/api/v1/accounts/1/contacts/search?q=+14155552671`

#### Headers:
```http
Content-Type: application/json
api_access_token: <CHATWOOT_API_ACCESS_TOKEN>
```

---

### Create Incoming Message from WhatsApp
`POST http://chatwoot-web:3000/api/v1/accounts/1/conversations/{conversation_id}/messages`

#### Headers:
```http
Content-Type: application/json
api_access_token: <CHATWOOT_API_ACCESS_TOKEN>
```

#### Request Payload:
```json
{
  "content": "My monitor is flickering and turning black. #ticket",
  "message_type": "incoming"
}
```
*`message_type`: `incoming` (from WhatsApp user), `outgoing` (agent/AI reply).*

