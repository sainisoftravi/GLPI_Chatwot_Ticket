import logging
import httpx
from typing import Optional, Dict, Any
from config import settings

logger = logging.getLogger("openwa_client")

class OpenWAClient:
    def __init__(self):
        self.base_url = settings.openwa_base_url
        self.api_key = settings.openwa_api_key
        self.session_name = settings.openwa_session_name

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """
        Sends a WhatsApp message via OpenWA.
        chat_id format: '1234567890@c.us' or just digits like '1234567890'.
        """
        if not chat_id.endswith("@c.us") and not chat_id.endswith("@g.us"):
            # Strip '+' and whitespace
            clean_id = chat_id.replace("+", "").replace(" ", "").replace("-", "")
            chat_id = f"{clean_id}@c.us"

        url = f"{self.base_url}/api/sessions/{self.session_name}/messages/send-text"
        payload = {
            "chatId": chat_id,
            "text": text
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code not in (200, 201):
                    logger.error(f"OpenWA send failed ({resp.status_code}): {resp.text}")
                    return {"status": "error", "error": resp.text}
                logger.info(f"OpenWA successfully delivered message to {chat_id}")
                return resp.json()
        except Exception as e:
            logger.error(f"Exception while sending message via OpenWA: {e}")
            return {"status": "error", "error": str(e)}

    async def get_session_status(self) -> Dict[str, Any]:
        """Checks WhatsApp connection status of the session."""
        url = f"{self.base_url}/api/sessions/{self.session_name}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    return resp.json()
                return {"status": "offline", "code": resp.status_code}
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
