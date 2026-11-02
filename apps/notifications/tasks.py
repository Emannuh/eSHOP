"""Celery tasks for notifications."""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_payment_confirmation(order_pk: int) -> str:
    """Send SMS and email confirmation after a successful payment."""
    from apps.notifications.services import (
        send_order_confirmation_email,
        send_order_confirmation_sms,
    )
    from apps.orders.models import Order

    try:
        order = Order.objects.get(pk=order_pk)
    except Order.DoesNotExist:
        logger.error("send_payment_confirmation: Order %s not found", order_pk)
        return "Order not found."

    send_order_confirmation_sms(order)
    send_order_confirmation_email(order)
    return f"Notifications sent for order {order.reference}."
