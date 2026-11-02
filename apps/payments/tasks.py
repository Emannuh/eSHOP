"""
Celery tasks for payment status checks.

check_pending_payments:
    Queries STK Push status for transactions still PENDING after 60 seconds.
    Designed to be run periodically (e.g., every 2 minutes via Celery Beat).
"""
import logging

from celery import shared_task
from django.utils import timezone

from .models import MpesaTransaction
from .services import DarajaService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def check_pending_payments(self) -> str:
    """Query Daraja for transactions stuck in PENDING > 60 seconds."""
    cutoff = timezone.now() - timezone.timedelta(seconds=60)
    pending_txns = MpesaTransaction.objects.filter(
        status=MpesaTransaction.Status.PENDING,
        created_at__lte=cutoff,
    ).select_related("order")

    count = pending_txns.count()
    if count == 0:
        return "No pending transactions."

    service = DarajaService()
    processed = 0

    for txn in pending_txns:
        result = service.stk_query(txn.checkout_request_id)
        if "error" in result:
            logger.warning("STK Query error for %s: %s", txn.checkout_request_id, result["error"])
            continue

        result_code_str = result.get("ResultCode")
        if result_code_str is None:
            continue

        try:
            result_code = int(result_code_str)
        except (ValueError, TypeError):
            continue

        from apps.payments.views import _handle_failure, _handle_success

        # Wrap in a minimal stk_callback shape to reuse the existing handlers
        pseudo_callback = {
            "CheckoutRequestID": txn.checkout_request_id,
            "MerchantRequestID": txn.merchant_request_id,
            "ResultCode": result_code,
            "ResultDesc": result.get("ResultDesc", ""),
        }

        if result_code == 0:
            _handle_success(txn, pseudo_callback, result)
        elif result_code != 1032:  # 1032 = request in process / still pending
            _handle_failure(txn, result_code, result.get("ResultDesc", ""), result)

        processed += 1

    return f"Processed {processed}/{count} pending transactions."
