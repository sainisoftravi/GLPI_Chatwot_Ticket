import logging
import httpx
from typing import Optional, Dict, Any
from config import settings

logger = logging.getLogger("glpi_client")

class GLPIClient:
    def __init__(self):
        self.base_url = f"{settings.glpi_base_url}/apirest.php"
        self.app_token = settings.glpi_app_token
        self.user_token = settings.glpi_user_token
        self.session_token: Optional[str] = None

    async def _init_session(self) -> str:
        """Initializes a session with GLPI REST API."""
        url = f"{self.base_url}/initSession"
        headers = {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Authorization": f"user_token {self.user_token}"
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"GLPI initSession failed: {resp.status_code} - {resp.text}")
                resp.raise_for_status()
            data = resp.json()
            self.session_token = data.get("session_token")
            logger.info("Successfully established GLPI session.")
            return self.session_token

    async def _get_headers(self) -> Dict[str, str]:
        if not self.session_token:
            await self._init_session()
        return {
            "Content-Type": "application/json",
            "App-Token": self.app_token,
            "Session-Token": self.session_token
        }

    async def create_ticket(
        self,
        title: str,
        content: str,
        urgency: int = 3, # 1: Very Low, 2: Low, 3: Medium, 4: High, 5: Very High
        category_id: Optional[int] = None,
        chatwoot_conversation_id: Optional[int] = None,
        requester_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Creates a new ITIL Ticket in GLPI."""
        url = f"{self.base_url}/Ticket"
        headers = await self._get_headers()

        # Format rich content with Chatwoot/WhatsApp reference
        formatted_content = f"{content}\n\n<hr/>"
        if requester_info:
            formatted_content += f"<p><b>Requester Name:</b> {requester_info.get('name', 'N/A')}<br/>"
            formatted_content += f"<b>WhatsApp / Phone:</b> {requester_info.get('phone_number', 'N/A')}<br/>"
            formatted_content += f"<b>Email:</b> {requester_info.get('email', 'N/A')}</p>"
        if chatwoot_conversation_id:
            cw_link = f"{settings.chatwoot_base_url}/app/accounts/{settings.chatwoot_account_id}/conversations/{chatwoot_conversation_id}"
            formatted_content += f"<p><b>Chatwoot Live Thread:</b> <a href='{cw_link}'>View Conversation #{chatwoot_conversation_id}</a></p>"

        payload = {
            "input": {
                "name": title,
                "content": formatted_content,
                "urgency": urgency,
                "status": 1, # 1 = New, 2 = Assigned (Processing), 3 = Planned, 4 = Pending, 5 = Solved, 6 = Closed
                "type": 1, # 1 = Incident, 2 = Request
                "itilcategories_id": category_id or settings.default_ticket_category_id
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            # If session expired, retry once
            if resp.status_code == 401:
                logger.warning("GLPI session expired, renewing session...")
                await self._init_session()
                headers = await self._get_headers()
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code not in (200, 201):
                logger.error(f"Failed to create GLPI Ticket: {resp.status_code} - {resp.text}")
                resp.raise_for_status()

            ticket_data = resp.json()
            ticket_id = ticket_data.get("id")
            logger.info(f"Created GLPI Ticket #{ticket_id}: {title}")

            # Automatically add an initial task for the IT Kanban board
            await self.add_ticket_task(
                ticket_id=ticket_id,
                task_content="Initial Triage & Diagnostics (Auto-generated from WhatsApp/Chat AI Escalation)",
                state=1 # 1 = To Do, 2 = Information Required, 3 = In Progress, 4 = Done
            )

            return ticket_data

    async def add_ticket_task(
        self,
        ticket_id: int,
        task_content: str,
        state: int = 1
    ) -> Dict[str, Any]:
        """Creates a sub-task on the GLPI Ticket for IT Kanban tracking."""
        url = f"{self.base_url}/TicketTask"
        headers = await self._get_headers()
        payload = {
            "input": {
                "tickets_id": ticket_id,
                "content": task_content,
                "state": state
            }
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in (200, 201):
                logger.info(f"Added task to GLPI Ticket #{ticket_id}")
                return resp.json()
            else:
                logger.warning(f"Could not add task to GLPI Ticket #{ticket_id}: {resp.text}")
                return {}

    async def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """Retrieves ticket details from GLPI."""
        url = f"{self.base_url}/Ticket/{ticket_id}"
        headers = await self._get_headers()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            resp.raise_for_status()
