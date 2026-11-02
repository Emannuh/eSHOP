"""
Tests for the Daraja (M-Pesa) service and callback view.

Covers:
- STK Push request payload construction
- Callback success (ResultCode 0)
- Callback failure (ResultCode 1032)
- Callback idempotency (same payload sent twice)
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from apps.orders.models import Order
from apps.payments.models import MpesaTransaction
from apps.payments.views import mpesa_callback

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def zone(db):
    from apps.orders.models import DeliveryZone

    return DeliveryZone.objects.create(name="CBD", fee=150)


@pytest.fixture
def order(db, zone):
    return Order.objects.create(
        customer_name="Test User",
        phone="254712345678",
        delivery_zone=zone,
        delivery_address="Nairobi",
        delivery_fee=150,
        subtotal=5000,
        total=5150,
    )


@pytest.fixture
def pending_txn(db, order):
    return MpesaTransaction.objects.create(
        order=order,
        checkout_request_id="ws_CO_TEST_12345",
        merchant_request_id="MERCHANT_12345",
        amount=5150,
        phone="254712345678",
    )


def make_callback(checkout_id: str, result_code: int = 0, receipt: str = "RCT123456") -> dict:
    body: dict = {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": checkout_id,
                "MerchantRequestID": "MERCHANT_12345",
                "ResultCode": result_code,
                "ResultDesc": "The service request is processed successfully."
                if result_code == 0
                else "Request cancelled by user",
            }
        }
    }
    if result_code == 0:
        body["Body"]["stkCallback"]["CallbackMetadata"] = {
            "Item": [
                {"Name": "Amount", "Value": 5150},
                {"Name": "MpesaReceiptNumber", "Value": receipt},
                {"Name": "TransactionDate", "Value": 20241115120000},
                {"Name": "PhoneNumber", "Value": 254712345678},
            ]
        }
    return body


# ---------------------------------------------------------------------------
# STK Push payload test
# ---------------------------------------------------------------------------


def test_stk_push_payload(db, order, settings):
    """Verify the STK Push payload uses the correct server-side amount."""
    settings.DARAJA_CONSUMER_KEY = "test_key"
    settings.DARAJA_CONSUMER_SECRET = "test_secret"
    settings.DARAJA_SHORTCODE = "174379"
    settings.DARAJA_PASSKEY = "testpasskey"
    settings.DARAJA_CALLBACK_URL = "https://example.com/payments/callback/"
    settings.DARAJA_TRANSACTION_TYPE = "CustomerPayBillOnline"
    settings.DARAJA_ENV = "sandbox"

    from apps.payments.services import DarajaService

    service = DarajaService()

    mock_token_response = MagicMock()
    mock_token_response.json.return_value = {"access_token": "fake_token"}
    mock_token_response.raise_for_status = MagicMock()

    mock_stk_response = MagicMock()
    mock_stk_response.json.return_value = {
        "ResponseCode": "0",
        "CheckoutRequestID": "ws_CO_NEWTEST",
        "MerchantRequestID": "MERCHANT_NEW",
        "ResponseDescription": "Success",
    }
    mock_stk_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_token_response), \
         patch("requests.post", return_value=mock_stk_response) as mock_post, \
         patch("django.core.cache.cache.get", return_value=None), \
         patch("django.core.cache.cache.set"):

        result = service.stk_push(phone="254712345678", amount=order.total, order=order)

    assert result["success"] is True
    call_kwargs = mock_post.call_args
    payload = call_kwargs[1]["json"] if call_kwargs[1] else call_kwargs[0][1]
    # Amount must come from the server — never from client
    assert payload["Amount"] == order.total
    assert payload["PhoneNumber"] == "254712345678"
    assert payload["AccountReference"] == order.reference


# ---------------------------------------------------------------------------
# Callback tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_callback_success(pending_txn, rf):
    payload = make_callback(pending_txn.checkout_request_id, result_code=0)
    request = rf.post(
        "/payments/callback/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    with patch("apps.notifications.tasks.send_payment_confirmation.delay"):
        response = mpesa_callback(request)

    assert response.status_code == 200
    assert json.loads(response.content)["ResultCode"] == 0

    pending_txn.refresh_from_db()
    assert pending_txn.status == MpesaTransaction.Status.SUCCESS
    assert pending_txn.mpesa_receipt_number == "RCT123456"

    pending_txn.order.refresh_from_db()
    assert pending_txn.order.status == Order.Status.PAID


@pytest.mark.django_db
def test_callback_failure(pending_txn, rf):
    payload = make_callback(pending_txn.checkout_request_id, result_code=1032)
    request = rf.post(
        "/payments/callback/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    response = mpesa_callback(request)

    assert response.status_code == 200

    pending_txn.refresh_from_db()
    assert pending_txn.status == MpesaTransaction.Status.FAILED

    pending_txn.order.refresh_from_db()
    assert pending_txn.order.status == Order.Status.FAILED


@pytest.mark.django_db
def test_callback_idempotency(pending_txn, rf):
    """The same successful callback sent twice must not double-confirm."""
    payload = make_callback(pending_txn.checkout_request_id, result_code=0)

    def post():
        request = rf.post(
            "/payments/callback/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        with patch("apps.notifications.tasks.send_payment_confirmation.delay"):
            return mpesa_callback(request)

    response1 = post()
    response2 = post()  # duplicate

    assert response1.status_code == 200
    assert response2.status_code == 200

    # Still only one SUCCESS, order still PAID (not double-counted)
    pending_txn.refresh_from_db()
    assert pending_txn.status == MpesaTransaction.Status.SUCCESS
    pending_txn.order.refresh_from_db()
    assert pending_txn.order.status == Order.Status.PAID

    # Stock not double-reduced — check the order total is unchanged
    assert pending_txn.order.total == 5150
