import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # GLPI
    glpi_base_url: str = os.getenv("GLPI_BASE_URL", "http://glpi:80").rstrip("/")
    glpi_app_token: str = os.getenv("GLPI_APP_TOKEN", "")
    glpi_user_token: str = os.getenv("GLPI_USER_TOKEN", "")
    default_ticket_category_id: int = int(os.getenv("DEFAULT_TICKET_CATEGORY_ID", "1"))
    default_it_group_id: int = int(os.getenv("DEFAULT_IT_GROUP_ID", "1"))

    # Chatwoot
    chatwoot_base_url: str = os.getenv("CHATWOOT_BASE_URL", "http://chatwoot-web:3000").rstrip("/")
    chatwoot_api_access_token: str = os.getenv("CHATWOOT_API_ACCESS_TOKEN", "")
    chatwoot_account_id: int = int(os.getenv("CHATWOOT_ACCOUNT_ID", "1"))
    chatwoot_inbox_id: int = int(os.getenv("CHATWOOT_INBOX_ID", "1"))

    # OpenWA (Free WhatsApp Gateway)
    openwa_base_url: str = os.getenv("OPENWA_BASE_URL", "http://openwa:2785").rstrip("/")
    openwa_api_key: str = os.getenv("OPENWA_API_KEY", "")
    openwa_session_name: str = os.getenv("OPENWA_SESSION_NAME", "it-support")

    # Security & Trigger Rules
    bridge_secret_token: str = os.getenv("BRIDGE_SECRET_TOKEN", "secure_bridge_webhook_token_998877")
    auto_create_ticket_on_label: str = os.getenv("AUTO_CREATE_TICKET_ON_LABEL", "ticket-needed")
    public_glpi_url: str = os.getenv("PUBLIC_GLPI_URL", "http://localhost:8085").rstrip("/")

settings = Settings()

