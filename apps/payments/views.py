"""
Payments views.

- mpesa_callback: Daraja STK Push callback (csrf_exempt POST)
- Idempotent: repeated callbacks for the same checkout_request_id are safely ignored.
"""
from __future__ import annotations

import json
import logging

from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from apps.orders.models import Order

from .models import MpesaTransaction

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def mpesa_callback(request: HttpRequest) -> JsonResponse:
    """Receive and process the Safaricom STK Push callback.

    Always returns HTTP 200 with {"ResultCode": 0, "ResultDesc": "Accepted"}
    so Safaricom does not retry indefinitely.

    Idempotency: if this callback has already been processed (transaction
    status != PENDING), we log it and return immediately without touching
    the order again.
    """
    # Always ack Safaricom first, regardless of processing outcome
    ack = JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.error("Daraja callback: could not parse JSON body")
        return ack

    logger.info("Daraja callback received: %s", json.dumps(body))

    try:
        stk_callback = body["Body"]["stkCallback"]
        checkout_request_id = stk_callback["CheckoutRequestID"]
        result_code = int(stk_callback["ResultCode"])
        result_desc = stk_callback.get("ResultDesc", "")
    except (KeyError, ValueError, TypeError) as exc:
        logger.error("Daraja callback: malformed payload — %s", exc)
        return ack

    # Fetch the transaction record
    try:
        txn = MpesaTransaction.objects.select_related("order").get(
            checkout_request_id=checkout_request_id
        )
    except MpesaTransaction.DoesNotExist:
        logger.warning(
            "Daraja callback: no transaction found for CheckoutRequestID %s",
            checkout_request_id,
        )
        return ack

    # Idempotency guard — if already processed, do nothing
    if txn.status != MpesaTransaction.Status.PENDING:
        logger.info(
            "Daraja callback: duplicate for %s (already %s) — ignored",
            checkout_request_id,
            txn.status,
        )
        return ack

    if result_code == 0:
        _handle_success(txn, stk_callback, body)
    else:
        _handle_failure(txn, result_code, result_desc, body)

    return ack


def _extract_metadata(callback_metadata: dict) -> dict:
    """Parse the CallbackMetadata items list into a flat dict."""
    result = {}
    for item in callback_metadata.get("Item", []):
        name = item.get("Name")
        value = item.get("Value")
        if name:
            result[name] = value
    return result


def _handle_success(
    txn: MpesaTransaction,
    stk_callback: dict,
    raw_body: dict,
) -> None:
    """Mark transaction SUCCESS, order PAID, reduce stock.

    All changes are wrapped in a single DB transaction for atomicity.
    """
    metadata = _extract_metadata(stk_callback.get("CallbackMetadata", {}))
    receipt = metadata.get("MpesaReceiptNumber", "")
    amount = int(metadata.get("Amount", txn.amount))

    with transaction.atomic():
        # Re-fetch inside the transaction with a lock to prevent races
        txn_locked = MpesaTransaction.objects.select_for_update().get(pk=txn.pk)

        # Double-check idempotency inside the lock
        if txn_locked.status != MpesaTransaction.Status.PENDING:
            logger.info("Daraja success: already processed (race condition avoided)")
            return

        txn_locked.status = MpesaTransaction.Status.SUCCESS
        txn_locked.result_code = 0
        txn_locked.result_desc = stk_callback.get("ResultDesc", "")
        txn_locked.mpesa_receipt_number = receipt
        txn_locked.raw_callback = raw_body
        txn_locked.save()

        order = txn_locked.order
        order.status = Order.Status.PAID
        order.save()

        # Reduce stock for each item
        for item in order.items.select_related("product"):
            if item.product:
                Product.objects.filter(pk=item.product_id).update(
                    stock=item.product.stock - item.quantity
                    if item.product.stock >= item.quantity
                    else 0
                )

    logger.info(
        "Order %s PAID — receipt %s — amount KES %s",
        txn.order.reference,
        receipt,
        amount,
    )

    # Fire post-payment notifications asynchronously
    try:
        from apps.notifications.tasks import send_payment_confirmation

        send_payment_confirmation.delay(txn.order.pk)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not queue notification for order %s: %s", txn.order.pk, exc)


def _handle_failure(
    txn: MpesaTransaction,
    result_code: int,
    result_desc: str,
    raw_body: dict,
) -> None:
    """Mark transaction and order FAILED."""
    with transaction.atomic():
        txn_locked = MpesaTransaction.objects.select_for_update().get(pk=txn.pk)
        if txn_locked.status != MpesaTransaction.Status.PENDING:
            return
        txn_locked.status = MpesaTransaction.Status.FAILED
        txn_locked.result_code = result_code
        txn_locked.result_desc = result_desc
        txn_locked.raw_callback = raw_body
        txn_locked.save()

        txn_locked.order.status = Order.Status.FAILED
        txn_locked.order.save()

    logger.info(
        "Order %s FAILED — code %s — %s",
        txn.order.reference,
        result_code,
        result_desc,
    )
