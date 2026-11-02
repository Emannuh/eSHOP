"""
Daraja (M-Pesa) service layer.

Handles:
- OAuth token fetch with in-memory/Redis caching
- STK Push (Lipa Na M-Pesa Online)
- STK Push Query (status check)

Settings read from Django settings (see config/settings/base.py).
Never logs secrets.
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

from apps.orders.models import Order

from .models import MpesaTransaction

logger = logging.getLogger(__name__)

SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE = "https://api.safaricom.co.ke"

TOKEN_CACHE_KEY = "daraja_access_token"
TOKEN_CACHE_TTL = 3500  # seconds — token expires in 3600 s


class DarajaService:
    """Thin service class wrapping the Daraja API.

    All methods raise nothing — errors are returned in the result dict so
    the view can decide what to show the user.
    """

    def __init__(self) -> None:
        self.base_url = (
            PRODUCTION_BASE
            if settings.DARAJA_ENV == "production"
            else SANDBOX_BASE
        )
        self.consumer_key: str = settings.DARAJA_CONSUMER_KEY
        self.consumer_secret: str = settings.DARAJA_CONSUMER_SECRET
        self.shortcode: str = settings.DARAJA_SHORTCODE
        self.passkey: str = settings.DARAJA_PASSKEY
        self.callback_url: str = settings.DARAJA_CALLBACK_URL
        self.transaction_type: str = settings.DARAJA_TRANSACTION_TYPE

    # ------------------------------------------------------------------
    # Token
    # ------------------------------------------------------------------

    def get_access_token(self) -> str | None:
        """Return a valid OAuth token, using cache when possible."""
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            return cached

        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        try:
            resp = requests.get(
                f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {credentials}"},
                timeout=10,
            )
            resp.raise_for_status()
            token = resp.json().get("access_token")
            if token:
                cache.set(TOKEN_CACHE_KEY, token, TOKEN_CACHE_TTL)
            return token
        except requests.RequestException as exc:
            logger.error("Daraja token fetch failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # STK Push
    # ------------------------------------------------------------------

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _password(self, timestamp: str) -> str:
        """Generate the base64-encoded password for STK Push."""
        raw = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    def stk_push(
        self, phone: str, amount: int, order: Order
    ) -> dict[str, Any]:
        """Initiate an STK Push and persist the MpesaTransaction record.

        Args:
            phone: Normalised phone number (254XXXXXXXXX).
            amount: Amount in KES (integer, server-side only).
            order: The associated Order instance.

        Returns:
            dict with keys: success (bool), error (str, if failed),
            checkout_request_id (str, if success).
        """
        token = self.get_access_token()
        if not token:
            return {"success": False, "error": "Could not authenticate with Daraja."}

        timestamp = self._timestamp()
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": self.transaction_type,
            "Amount": amount,
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": order.reference,
            "TransactionDesc": f"Payment for order {order.reference}",
        }

        try:
            resp = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("STK Push request failed for order %s: %s", order.reference, exc)
            return {"success": False, "error": "Payment gateway unavailable. Try again."}

        if data.get("ResponseCode") != "0":
            err = data.get("ResponseDescription", "STK Push failed.")
            logger.warning("STK Push rejected for order %s: %s", order.reference, err)
            return {"success": False, "error": err}

        # Persist the transaction record
        MpesaTransaction.objects.create(
            order=order,
            checkout_request_id=data["CheckoutRequestID"],
            merchant_request_id=data["MerchantRequestID"],
            amount=amount,
            phone=phone,
        )

        logger.info(
            "STK Push initiated for order %s — CheckoutRequestID: %s",
            order.reference,
            data["CheckoutRequestID"],
        )
        return {
            "success": True,
            "checkout_request_id": data["CheckoutRequestID"],
        }

    # ------------------------------------------------------------------
    # STK Push Query
    # ------------------------------------------------------------------

    def stk_query(self, checkout_request_id: str) -> dict[str, Any]:
        """Query the status of a pending STK Push.

        Returns the raw Daraja response dict, or {"error": ...} on failure.
        """
        token = self.get_access_token()
        if not token:
            return {"error": "Could not authenticate with Daraja."}

        timestamp = self._timestamp()
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("STK Query failed for %s: %s", checkout_request_id, exc)
            return {"error": str(exc)}
