import logging
import re
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any

from config import settings
from glpi_client import GLPIClient
from chatwoot_client import ChatwootClient
from openwa_client import OpenWAClient

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bridge_service")

app = FastAPI(
    title="GLPI <-> Chatwoot <-> OpenWA IT Ticket Bridge",
    version="2.0.0",
    description="Connects Open-Source WhatsApp (OpenWA), Chatwoot AI, and GLPI ITIL Ticketing & Task Kanban."
)

glpi = GLPIClient()
chatwoot = ChatwootClient()
openwa = OpenWAClient()

processed_events = set()

def clean_event_id(event_id: str):
    if len(processed_events) > 1000:
        processed_events.clear()
    processed_events.add(event_id)

async def process_chatwoot_to_glpi(payload: Dict[str, Any]):
    """Background worker that extracts Chatwoot conversation data and creates a GLPI ticket."""
    event = payload.get("event")
    conversation = payload.get("conversation", {})
    conversation_id = conversation.get("id") or payload.get("id")

    if not conversation_id:
        logger.warning("No conversation ID found in payload.")
        return

    # Check for existing ticket label
    labels = conversation.get("labels", [])
    for label in labels:
        if str(label).startswith("glpi-ticket-"):
            logger.info(f"Conversation #{conversation_id} already has a ticket linked ({label}). Skipping.")
            return

    meta = payload.get("meta", {})
    sender = meta.get("sender", {})
    sender_name = sender.get("name") or "WhatsApp User"
    sender_phone = sender.get("phone_number") or sender.get("identifier") or "N/A"
    sender_email = sender.get("email") or "N/A"

    requester_info = {
        "name": sender_name,
        "phone_number": sender_phone,
        "email": sender_email
    }

    content = payload.get("content") or ""
    if not content or len(content.strip()) < 5:
        history = await chatwoot.get_messages(conversation_id)
        user_msgs = [m.get("content") for m in history if m.get("message_type") == 0 and m.get("content")]
        content = "\n".join(user_msgs[-5:]) if user_msgs else "New IT Support Request via WhatsApp"

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

        # 2. Tag conversation in Chatwoot
        await chatwoot.add_labels(conversation_id, [f"glpi-ticket-{ticket_id}", "it-dispatched"])

        # 3. Post internal note for technicians
        internal_note = (
            f"✅ **GLPI ITIL Ticket Created**\n"
            f"- **Ticket ID:** #{ticket_id}\n"
            f"- **Kanban Status:** Initial Triage (To Do)\n"
            f"- **GLPI Link:** [Open Ticket #{ticket_id}]({glpi_ticket_link})"
        )
        await chatwoot.send_message(conversation_id, internal_note, is_private=True)

        # 4. Send customer notification via OpenWA / Chatwoot
        public_reply = (
            f"🎫 Hello! Your request has been logged in our IT Management System.\n\n"
            f"• Ticket Number: *#{ticket_id}*\n"
            f"• Status: *Assigned to IT Support Team*\n\n"
            f"An IT technician is investigating. You will receive updates directly here on WhatsApp."
        )
        await chatwoot.send_message(conversation_id, public_reply, is_private=False)

        # Also dispatch directly via OpenWA if phone is available
        if sender_phone and sender_phone != "N/A":
            await openwa.send_message(sender_phone, public_reply)

    except Exception as e:
        logger.exception(f"Error handling Chatwoot->GLPI sync for conversation #{conversation_id}: {e}")

@app.get("/health")
async def health_check():
    openwa_status = await openwa.get_session_status()
    return {
        "status": "healthy",
        "service": "glpi-chatwoot-openwa-bridge",
        "glpi_target": settings.glpi_base_url,
        "chatwoot_target": settings.chatwoot_base_url,
        "openwa_target": settings.openwa_base_url,
        "openwa_session": openwa_status
    }

@app.post("/webhook/openwa")
async def handle_openwa_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives incoming WhatsApp messages from OpenWA gateway.
    Routes to Chatwoot for AI / Agent handling and checks for IT ticket triggers.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event") or payload.get("type")
    data = payload.get("data") or payload

    # Ignore outgoing messages sent by the bot itself
    if data.get("fromMe") is True:
        return {"status": "ignored_self_message"}

    # Extract sender & message body
    chat_id = data.get("chatId") or data.get("from") or ""
    sender_name = data.get("notifyName") or data.get("sender", {}).get("name") or chat_id.split("@")[0]
    body = (data.get("body") or data.get("text") or "").strip()

    if not chat_id or not body:
        return {"status": "no_content_or_chat_id"}

    logger.info(f"Incoming WhatsApp message from {chat_id} ({sender_name}): {body[:40]}...")

    # Forward message into Chatwoot API Channel
    contact_id = await chatwoot.get_or_create_contact(name=sender_name, phone_number=chat_id)
    if contact_id:
        conversation_id = await chatwoot.get_or_create_conversation(contact_id=contact_id, source_id=chat_id)
        if conversation_id:
            await chatwoot.create_incoming_message(conversation_id, body)

            # Check if this message triggers an IT Ticket directly
            if body.lower().startswith("#ticket") or body.lower().startswith("/ticket"):
                synth_payload = {
                    "event": "message_created",
                    "id": conversation_id,
                    "content": body,
                    "conversation": {"id": conversation_id, "labels": []},
                    "meta": {"sender": {"name": sender_name, "phone_number": chat_id}}
                }
                background_tasks.add_task(process_chatwoot_to_glpi, synth_payload)

    return {"status": "routed_to_chatwoot"}

@app.post("/webhook/chatwoot")
async def handle_chatwoot_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives events from Chatwoot.
    1. If outgoing message from Agent/AI -> forwards to OpenWA (WhatsApp user).
    2. If trigger #ticket or label ticket-needed -> creates GLPI ticket.
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

    # 1. Forward outgoing replies from Chatwoot (AI or Technician) to WhatsApp via OpenWA
    if event == "message_created" and payload.get("message_type") == "outgoing" and not payload.get("private"):
        content = payload.get("content") or ""
        conversation = payload.get("conversation", {})
        meta = payload.get("meta", {})
        sender = meta.get("sender", {})
        phone = sender.get("phone_number") or conversation.get("meta", {}).get("sender", {}).get("phone_number")
        if phone:
            logger.info(f"Relaying Chatwoot outgoing message to WhatsApp ({phone}) via OpenWA")
            await openwa.send_message(phone, content)

    # 2. Check for Ticket Escalation triggers
    should_create_ticket = False
    if event == "message_created" and payload.get("message_type") == "incoming":
        content = (payload.get("content") or "").strip().lower()
        if content.startswith("#ticket") or content.startswith("/ticket"):
            should_create_ticket = True
    elif event in ("conversation_updated", "conversation_created"):
        labels = payload.get("labels", [])
        if settings.auto_create_ticket_on_label in labels or "escalate-it" in labels:
            should_create_ticket = True

    if should_create_ticket:
        background_tasks.add_task(process_chatwoot_to_glpi, payload)
        return {"status": "ticket_creation_queued"}

    return {"status": "processed", "event": event}

@app.post("/webhook/glpi")
async def handle_glpi_webhook(request: Request):
    """
    Receives notification events from GLPI when a technician solves or updates a ticket.
    Relays update back to WhatsApp via OpenWA and Chatwoot.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    ticket_id = payload.get("ticket_id")
    status = payload.get("status")
    solution = payload.get("solution") or payload.get("comment", "")
    conversation_id = payload.get("chatwoot_conversation_id")
    phone_number = payload.get("phone_number")

    if not conversation_id and ticket_id:
        try:
            ticket = await glpi.get_ticket(int(ticket_id))
            content = ticket.get("content", "")
            match = re.search(r"conversations/(\d+)", content)
            if match:
                conversation_id = int(match.group(1))
            phone_match = re.search(r"WhatsApp / Phone:</b>\s*([+\d\s-]+)", content)
            if phone_match and not phone_number:
                phone_number = phone_match.group(1).strip()
        except Exception as e:
            logger.warning(f"Could not parse details from ticket #{ticket_id}: {e}")

    update_text = (
        f"📢 *IT Ticket Update* (Ticket #{ticket_id})\n\n"
        f"Status: *{status or 'Updated'}*\n"
    )
    if solution:
        update_text += f"Notes: {solution}\n\n"
    update_text += "If you have any further questions, simply reply here!"

    if conversation_id:
        await chatwoot.send_message(conversation_id, update_text, is_private=False)
    if phone_number and phone_number != "N/A":
        await openwa.send_message(phone_number, update_text)

    return {"status": "relayed_to_chatwoot_and_openwa"}
