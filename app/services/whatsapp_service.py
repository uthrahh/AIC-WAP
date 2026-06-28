import httpx
from loguru import logger

from app.core.config import get_settings


class WhatsAppService:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.whatsapp_gateway_url.rstrip("/")

    def send_message(self, text: str, group: bool = True) -> bool:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/send",
                    json={"message": text, "group": group},
                )
                response.raise_for_status()
                return True
        except Exception as exc:
            logger.error(f"WhatsApp send failed: {exc}")
            return False

    def fetch_messages(self, start_iso: str, end_iso: str) -> list[dict]:
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(
                    f"{self.base_url}/messages",
                    params={"start": start_iso, "end": end_iso},
                )
                response.raise_for_status()
                return response.json().get("messages", [])
        except Exception as exc:
            logger.warning(f"WhatsApp fetch fallback to DB: {exc}")
            return []


whatsapp_service = WhatsAppService()
