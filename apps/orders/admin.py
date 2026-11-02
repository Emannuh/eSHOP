"""Admin configuration for the orders app."""
import csv
from typing import Any

from django.contrib import admin
from django.http import HttpResponse

from .models import DeliveryZone, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "product_price", "quantity", "subtotal")
    can_delete = False


def mark_processing(modeladmin: Any, request: Any, queryset: Any) -> None:
    queryset.filter(status=Order.Status.PAID).update(status=Order.Status.PROCESSING)


mark_processing.short_description = "Mark selected paid orders as Processing"


def mark_delivered(modeladmin: Any, request: Any, queryset: Any) -> None:
    queryset.filter(status=Order.Status.PROCESSING).update(status=Order.Status.DELIVERED)


mark_delivered.short_description = "Mark selected processing orders as Delivered"


def export_orders_csv(modeladmin: Any, request: Any, queryset: Any) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="orders.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Reference", "Customer", "Phone", "Email",
        "Delivery Zone", "Subtotal", "Delivery Fee", "Total",
        "Status", "Created",
    ])
    for o in queryset.select_related("delivery_zone"):
        writer.writerow([
            o.reference, o.customer_name, o.phone, o.email,
            o.delivery_zone.name, o.subtotal, o.delivery_fee, o.total,
            o.status, o.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    return response


export_orders_csv.short_description = "Export selected orders as CSV"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "customer_name", "phone", "total_display",
        "status", "delivery_zone", "created_at",
    )
    list_filter = ("status", "delivery_zone", "created_at")
    search_fields = ("reference", "customer_name", "phone", "email")
    readonly_fields = (
        "reference", "phone", "subtotal", "delivery_fee", "total",
        "created_at", "updated_at",
    )
    inlines = [OrderItemInline]
    actions = [mark_processing, mark_delivered, export_orders_csv]
    date_hierarchy = "created_at"

    def total_display(self, obj: Order) -> str:
        return obj.total_display

    total_display.short_description = "Total"
    total_display.admin_order_field = "total"


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "fee", "is_active")
    list_editable = ("fee", "is_active")
