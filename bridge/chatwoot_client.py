import logging
import httpx
from typing import Optional, Dict, Any, List
from config import settings

logger = logging.getLogger("chatwoot_client")

class ChatwootClient:
    def __init__(self):
        self.base_url = f"{settings.chatwoot_base_url}/api/v1/accounts/{settings.chatwoot_account_id}"
        self.api_token = settings.chatwoot_api_access_token

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "api_access_token": self.api_token
        }

    async def get_or_create_contact(self, name: str, phone_number: str) -> int:
        """Finds or creates a contact in Chatwoot."""
        clean_phone = phone_number.replace("@c.us", "").replace("@g.us", "")
        if not clean_phone.startswith("+"):
            clean_phone = f"+{clean_phone}"

        search_url = f"{self.base_url}/contacts/search?q={clean_phone}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(search_url, headers=self._get_headers())
                if res.status_code == 200:
                    contacts = res.json().get("payload", [])
                    if contacts:
                        return contacts[0]["id"]
            except Exception as e:
                logger.warning(f"Contact search failed: {e}")

            # Create if not found
            create_url = f"{self.base_url}/contacts"
            payload = {
                "inbox_id": settings.chatwoot_inbox_id,
                "name": name or clean_phone,
                "phone_number": clean_phone
            }
            try:
                create_res = await client.post(create_url, json=payload, headers=self._get_headers())
                if create_res.status_code in (200, 201):
                    return create_res.json()["payload"]["contact"]["id"]
            except Exception as e:
                logger.error(f"Contact creation failed: {e}")
        return 0

    async def get_or_create_conversation(self, contact_id: int, source_id: str) -> int:
        """Finds or creates an open conversation for this contact."""
        url = f"{self.base_url}/conversations"
        payload = {
            "source_id": source_id,
            "inbox_id": settings.chatwoot_inbox_id,
            "contact_id": contact_id,
            "status": "open"
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code in (200, 201):
                    return resp.json().get("id")
            except Exception as e:
                logger.error(f"Failed to get/create conversation: {e}")
        return 0

    async def create_incoming_message(self, conversation_id: int, content: str) -> Dict[str, Any]:
        """Creates an incoming message from WhatsApp into Chatwoot."""
        url = f"{self.base_url}/conversations/{conversation_id}/messages"
        payload = {
            "content": content,
            "message_type": "incoming"
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self._get_headers())
            return resp.json() if resp.status_code in (200, 201) else {}

    async def send_message(
        self,
        conversation_id: int,
        content: str,
        is_private: bool = False
    ) -> Dict[str, Any]:
        """
        Sends an outgoing message or private note to Chatwoot conversation.
        """
        url = f"{self.base_url}/conversations/{conversation_id}/messages"
        payload = {
            "content": content,
            "message_type": "outgoing",
            "private": is_private
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self._get_headers())
            if resp.status_code not in (200, 201):
                logger.error(f"Failed to send message to Chatwoot #{conversation_id}: {resp.status_code} - {resp.text}")
                return {}
            logger.info(f"Message sent to Chatwoot #{conversation_id} (private={is_private})")
            return resp.json()

    async def add_labels(self, conversation_id: int, labels: List[str]) -> Dict[str, Any]:
        """Adds labels to the conversation."""
        url = f"{self.base_url}/conversations/{conversation_id}/labels"
        payload = {"labels": labels}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self._get_headers())
            return resp.json() if resp.status_code in (200, 201) else {}

    async def get_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Fetches conversation history."""
        url = f"{self.base_url}/conversations/{conversation_id}/messages"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 200:
                data = resp.json()
                return data.get("payload", [])
            return []
