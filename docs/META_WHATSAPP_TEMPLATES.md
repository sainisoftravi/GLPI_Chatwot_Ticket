# Meta WhatsApp Business Message Templates

Use these templates in the **Meta Business Suite > WhatsApp Manager > Message Templates** to ensure compliance with WhatsApp's 24-hour customer service window rules.

---

### Template 1: Ticket Created Confirmation
- **Category:** `Utility`
- **Template Name:** `it_ticket_created`
- **Language:** `English (en_US)`
- **Header:** None or Text: `IT Support Dispatch`
- **Body:**
```text
Hello {{1}},

Your IT support request has been logged successfully.

• Ticket ID: #{{2}}
• Issue: {{3}}
• Status: Assigned to Technician

An IT engineer has been dispatched to investigate. We will send you updates directly on this thread.
```
- **Sample Values:**
  - `{{1}}`: Alex
  - `{{2}}`: 1042
  - `{{3}}`: VPN connection error 403

---

### Template 2: Ticket Status Update / Technician Note
- **Category:** `Utility`
- **Template Name:** `it_ticket_status_update`
- **Language:** `English (en_US)`
- **Body:**
```text
Hello {{1}},

An update has been posted to your IT Ticket #{{2}}.

• Status: {{3}}
• Technician Note: {{4}}

Please reply directly to this message if you have any questions.
```
- **Sample Values:**
  - `{{1}}`: Alex
  - `{{2}}`: 1042
  - `{{3}}`: In Progress (Hardware Diagnostics)
  - `{{4}}`: Replacement docking station is scheduled for delivery today.

---

### Template 3: Ticket Resolved & Closed
- **Category:** `Utility`
- **Template Name:** `it_ticket_resolved`
- **Language:** `English (en_US)`
- **Body:**
```text
Hello {{1}},

Your IT Ticket #{{2}} has been marked as SOLVED.

• Resolution Summary: {{3}}

If the issue persists or if you need further help, simply reply to this message to reopen your ticket.
```
- **Sample Values:**
  - `{{1}}`: Alex
  - `{{2}}`: 1042
  - `{{3}}`: Network gateway reset and firmware updated.
