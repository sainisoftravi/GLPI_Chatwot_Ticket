import logging
import re
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any

from config import settings
from glpi_client import GLPIClient
from chatwoot_client import ChatwootClient

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bridge_service")

app = FastAPI(
    title="GLPI <-> Chatwoot WhatsApp IT Ticket Bridge",
    version="1.0.0",
    description="Syncs WhatsApp / Live Chat conversations with GLPI ITIL Tickets & Kanban Task Boards."
)

glpi = GLPIClient()
chatwoot = ChatwootClient()

# In-memory deduplication set to avoid double-processing identical events
processed_events = set()

def clean_event_id(event_id: str):
    if len(processed_events) > 1000:
        processed_events.clear()
    processed_events.add(event_id)

async def process_chatwoot_to_glpi(payload: Dict[str, Any]):
    """
    Background worker that extracts Chatwoot conversation data and creates a GLPI ticket.
    """
    event = payload.get("event")
    conversation = payload.get("conversation", {})
    conversation_id = conversation.get("id") or payload.get("id")

    if not conversation_id:
        logger.warning("No conversation ID found in payload.")
        return

    # Check if conversation was already tagged with a GLPI ticket to avoid duplicates
    labels = conversation.get("labels", [])
    for label in labels:
        if str(label).startswith("glpi-ticket-"):
            logger.info(f"Conversation #{conversation_id} already has a ticket linked ({label}). Skipping.")
            return

    # Determine sender / requester info
    meta = payload.get("meta", {})
    sender = meta.get("sender", {})
    sender_name = sender.get("name") or "WhatsApp/Chat User"
    sender_phone = sender.get("phone_number") or sender.get("identifier") or "N/A"
    sender_email = sender.get("email") or "N/A"

    requester_info = {
        "name": sender_name,
        "phone_number": sender_phone,
        "email": sender_email
    }

    # Extract issue description
    content = payload.get("content") or ""
    # If this is triggered by label or status change, fetch recent conversation history
    if not content or len(content.strip()) < 5:
        history = await chatwoot.get_messages(conversation_id)
        user_msgs = [m.get("content") for m in history if m.get("message_type") == 0 and m.get("content")]
        content = "\n".join(user_msgs[-5:]) if user_msgs else "New IT Support Request via WhatsApp"

    # Clean trigger commands like #ticket or /ticket
    cleaned_content = re.sub(r"^[#/]ticket\s*", "", content, flags=re.IGNORECASE).strip()
    if not cleaned_content:
        cleaned_content = content

    ticket_title = f"IT Request from {sender_name}: {cleaned_content[:50]}..."

    try:
        # 1. Create Ticket in GLPI
        created_ticket = await glpi.create_ticket(
            title=ticket_title,
            content=cleaned_content,
            urgency=3,
            chatwoot_conversation_id=conversation_id,
            requester_info=requester_info
        )
        ticket_id = created_ticket.get("id")

        if not ticket_id:
            logger.error("GLPI ticket creation returned no ID.")
            return

        glpi_ticket_link = f"{settings.public_glpi_url}/front/ticket.form.php?id={ticket_id}"

        # 2. Tag Chatwoot conversation with the GLPI Ticket ID
        await chatwoot.add_labels(conversation_id, [f"glpi-ticket-{ticket_id}", "it-dispatched"])

        # 3. Post an internal private note for technicians in Chatwoot
        internal_note = (
            f"✅ **GLPI ITIL Ticket Created**\n"
            f"- **Ticket ID:** #{ticket_id}\n"
            f"- **Kanban Status:** Initial Triage (To Do)\n"
            f"- **GLPI Link:** [Open Ticket #{ticket_id}]({glpi_ticket_link})"
        )
        await chatwoot.send_message(conversation_id, internal_note, is_private=True)

        # 4. Send customer-facing WhatsApp / Live Chat acknowledgment
        public_reply = (
            f"🎫 Hello! Your request has been logged in our IT Management System.\n\n"
            f"• Ticket Number: *#{ticket_id}*\n"
            f"• Status: *Assigned to IT Support Team*\n\n"
            f"An IT technician is investigating. You will receive updates directly here on WhatsApp."
        )
        await chatwoot.send_message(conversation_id, public_reply, is_private=False)

    except Exception as e:
        logger.exception(f"Error handling Chatwoot->GLPI sync for conversation #{conversation_id}: {e}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "glpi-chatwoot-bridge",
        "glpi_target": settings.glpi_base_url,
        "chatwoot_target": settings.chatwoot_base_url
    }

@app.post("/webhook/chatwoot")
async def handle_chatwoot_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives events from Chatwoot webhooks.
    Triggers ticket creation on:
    1. Command: `#ticket` or `/ticket` in message
    2. Label: `ticket-needed` or `escalate-it` added to conversation
    3. Handoff: AI bot triggers IT escalation
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event")
    event_id = f"{event}_{payload.get('id', '')}_{payload.get('created_at', '')}"
    if event_id in processed_events:
        return {"status": "duplicate_skipped"}
    clean_event_id(event_id)

    should_create_ticket = False

    # Check 1: Message content contains trigger command
    if event == "message_created":
        content = (payload.get("content") or "").strip().lower()
        # Trigger on explicit command or if agent types #ticket in note
        if content.startswith("#ticket") or content.startswith("/ticket"):
            should_create_ticket = True

    # Check 2: Conversation labeled with trigger label
    elif event in ("conversation_updated", "conversation_created"):
        labels = payload.get("labels", [])
        if settings.auto_create_ticket_on_label in labels or "escalate-it" in labels:
            should_create_ticket = True

    if should_create_ticket:
        background_tasks.add_task(process_chatwoot_to_glpi, payload)
        return {"status": "ticket_creation_queued"}

    return {"status": "ignored_event", "event": event}

@app.post("/webhook/glpi")
async def handle_glpi_webhook(request: Request):
    """
    Receives notification events from GLPI when a technician solves or updates a ticket.
    Relays the update back to the customer on WhatsApp.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    ticket_id = payload.get("ticket_id")
    status = payload.get("status") # e.g. Solved (5) or Closed (6)
    solution = payload.get("solution") or payload.get("comment", "")
    conversation_id = payload.get("chatwoot_conversation_id")

    if not conversation_id and ticket_id:
        # Attempt to read ticket from GLPI to extract conversation_id if passed in payload
        try:
            ticket = await glpi.get_ticket(int(ticket_id))
            content = ticket.get("content", "")
            match = re.search(r"conversations/(\d+)", content)
            if match:
                conversation_id = int(match.group(1))
        except Exception as e:
            logger.warning(f"Could not parse conversation ID from ticket #{ticket_id}: {e}")

    if conversation_id:
        update_text = (
            f"📢 *IT Ticket Update* (Ticket #{ticket_id})\n\n"
            f"Status: *{status or 'Updated'}*\n"
        )
        if solution:
            update_text += f"Notes: {solution}\n\n"
        update_text += "If you have any further questions, simply reply here!"

        await chatwoot.send_message(conversation_id, update_text, is_private=False)
        return {"status": "message_relayed_to_whatsapp", "conversation_id": conversation_id}

    return {"status": "no_conversation_mapped"}
