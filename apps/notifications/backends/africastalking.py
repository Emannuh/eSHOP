"""Africa's Talking SMS backend."""
import logging

import requests
from django.conf import settings

from .base import BaseSmsBackend

logger = logging.getLogger(__name__)

AT_SEND_URL = "https://api.africastalking.com/version1/messaging"
AT_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"


class AfricasTalkingBackend(BaseSmsBackend):
    """Send SMS via Africa's Talking API."""

    def send(self, to: str, message: str) -> bool:
        username: str = settings.AFRICASTALKING_USERNAME
        api_key: str = settings.AFRICASTALKING_API_KEY
        sender_id: str = settings.AFRICASTALKING_SENDER_ID

        url = AT_SANDBOX_URL if username == "sandbox" else AT_SEND_URL
        payload = {
            "username": username,
            "to": to,
            "message": message,
        }
        if sender_id:
            payload["from"] = sender_id

        try:
            resp = requests.post(
                url,
                data=payload,
                headers={
                    "apiKey": api_key,
                    "Accept": "application/json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            recipients = data.get("SMSMessageData", {}).get("Recipients", [])
            if recipients and recipients[0].get("status") == "Success":
                return True
            logger.warning("AT SMS not delivered: %s", data)
            return False
        except requests.RequestException as exc:
            logger.error("Africa's Talking SMS error: %s", exc)
            return False
