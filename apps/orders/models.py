"""
Orders models: DeliveryZone, Order, OrderItem.

Phone numbers are stored in E.164 format: 254XXXXXXXXX (no +).
Prices are integers (KES).
"""
import uuid

from django.db import models

from apps.catalog.models import Product


class DeliveryZone(models.Model):
    """Configurable delivery areas with fees (managed in Django admin)."""

    name = models.CharField(max_length=150, unique=True)
    fee = models.PositiveIntegerField(help_text="Delivery fee in KES")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} — KES {self.fee}"


class Order(models.Model):
    """A customer order."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        PROCESSING = "PROCESSING", "Processing"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        FAILED = "FAILED", "Failed"

    reference = models.CharField(max_length=20, unique=True, editable=False)
    customer_name = models.CharField(max_length=200)
    # Stored as 254XXXXXXXXX
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    delivery_address = models.TextField()
    delivery_zone = models.ForeignKey(
        DeliveryZone,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    # Snapshot of zone fee at order time
    delivery_fee = models.PositiveIntegerField()
    subtotal = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reference"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Order {self.reference}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            # e.g. DKA-20241115-A3F2
            short_uuid = uuid.uuid4().hex[:4].upper()
            from django.utils import timezone
            date_part = timezone.now().strftime("%Y%m%d")
            self.reference = f"DKA-{date_part}-{short_uuid}"
        super().save(*args, **kwargs)

    @property
    def is_paid(self) -> bool:
        return self.status == self.Status.PAID

    @property
    def total_display(self) -> str:
        return f"KES {self.total:,}"


class OrderItem(models.Model):
    """A line item in an order — price is snapshotted at purchase time."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, null=True, blank=True
    )
    product_name = models.CharField(max_length=200)  # snapshot
    product_price = models.PositiveIntegerField()     # snapshot
    quantity = models.PositiveSmallIntegerField()
    subtotal = models.PositiveIntegerField()          # product_price × quantity

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.quantity}× {self.product_name}"

    def save(self, *args, **kwargs) -> None:
        self.subtotal = self.product_price * self.quantity
        super().save(*args, **kwargs)
