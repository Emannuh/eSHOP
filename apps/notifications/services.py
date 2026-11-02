"""
Notification service — thin adapter over the configurable SMS backend.
"""
from __future__ import annotations

import importlib
import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.notifications.backends.base import BaseSmsBackend
from apps.orders.models import Order

logger = logging.getLogger(__name__)


def get_sms_backend() -> BaseSmsBackend:
    """Instantiate the configured SMS backend."""
    backend_path: str = getattr(
        settings,
        "SMS_BACKEND",
        "apps.notifications.backends.console.ConsoleSmsBackend",
    )
    module_path, class_name = backend_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    klass = getattr(module, class_name)
    return klass()


def send_order_confirmation_sms(order: Order) -> None:
    """Send an SMS to the customer after a successful payment."""
    backend = get_sms_backend()
    message = (
        f"Hi {order.customer_name}, your order {order.reference} "
        f"of KES {order.total:,} has been received and is being processed. "
        f"Thank you for shopping with Duka!"
    )
    # Phone is stored as 254XXXXXXXXX; prepend + for international format
    to = f"+{order.phone}"
    try:
        backend.send(to=to, message=message)
    except Exception as exc:  # noqa: BLE001
        logger.error("SMS send failed for order %s: %s", order.reference, exc)


def send_order_confirmation_email(order: Order) -> None:
    """Send a confirmation email if the customer provided an address."""
    if not order.email:
        return
    subject = f"Order Confirmed — {order.reference}"
    body = (
        f"Hi {order.customer_name},\n\n"
        f"Thank you for your order!\n\n"
        f"Reference:  {order.reference}\n"
        f"Total:       KES {order.total:,}\n"
        f"Delivery to: {order.delivery_address}\n\n"
        f"We'll process your order shortly.\n\n"
        f"Duka Team"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Email send failed for order %s: %s", order.reference, exc)
