"""Admin configuration for the payments app (read-only)."""
from django.contrib import admin

from .models import MpesaTransaction


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "checkout_request_id_short",
        "order",
        "phone",
        "amount_display",
        "status",
        "mpesa_receipt_number",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("checkout_request_id", "mpesa_receipt_number", "phone", "order__reference")
    readonly_fields = (
        "order", "checkout_request_id", "merchant_request_id",
        "amount", "phone", "status", "result_code", "result_desc",
        "mpesa_receipt_number", "raw_callback", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def checkout_request_id_short(self, obj: MpesaTransaction) -> str:
        return obj.checkout_request_id[:24] + "…"

    checkout_request_id_short.short_description = "Checkout Request ID"

    def amount_display(self, obj: MpesaTransaction) -> str:
        return f"KES {obj.amount:,}"

    amount_display.short_description = "Amount"
    amount_display.admin_order_field = "amount"
