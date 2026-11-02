"""
Payment models: MpesaTransaction.

One transaction per order (OneToOne).
"""
from django.db import models

from apps.orders.models import Order


class MpesaTransaction(models.Model):
    """Record of a Daraja STK Push transaction."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="mpesa_transaction",
    )
    checkout_request_id = models.CharField(max_length=100, unique=True, db_index=True)
    merchant_request_id = models.CharField(max_length=100)
    amount = models.PositiveIntegerField(help_text="Amount in KES")
    phone = models.CharField(max_length=15)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.CharField(max_length=300, blank=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)
    # Full Safaricom callback payload for audit/debugging
    raw_callback = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"MPesa {self.checkout_request_id[:20]}… [{self.status}]"
