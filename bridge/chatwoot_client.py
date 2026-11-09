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

    async def send_message(
        self,
        conversation_id: int,
        content: str,
        is_private: bool = False
    ) -> Dict[str, Any]:
        """
        Sends a message to the Chatwoot conversation.
        If is_private=True, it appears as an internal team note.
        If is_private=False, it sends directly out to the WhatsApp / Live Chat user.
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
                logger.error(f"Failed to send message to Chatwoot conversation #{conversation_id}: {resp.status_code} - {resp.text}")
                resp.raise_for_status()
            logger.info(f"Message sent to Chatwoot #{conversation_id} (private={is_private})")
            return resp.json()

    async def add_labels(self, conversation_id: int, labels: List[str]) -> Dict[str, Any]:
        """Adds labels/tags to the conversation."""
        url = f"{self.base_url}/conversations/{conversation_id}/labels"
        payload = {"labels": labels}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self._get_headers())
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning(f"Failed to add labels {labels} to #{conversation_id}")
            return {}

    async def get_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Fetches conversation history to synthesize IT ticket context."""
        url = f"{self.base_url}/conversations/{conversation_id}/messages"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 200:
                data = resp.json()
                return data.get("payload", [])
            return []

