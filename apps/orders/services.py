"""
Order business logic.

All totals are computed server-side. Never trust amounts from the client.
"""
from __future__ import annotations

import re

from django.db import transaction

from apps.cart.cart import Cart
from apps.catalog.models import Product

from .models import DeliveryZone, Order, OrderItem

# ---------------------------------------------------------------------------
# Phone normalisation
# ---------------------------------------------------------------------------

KENYAN_PHONE_RE = re.compile(
    r"^(?:"
    r"\+?254(\d{9})"      # +254XXXXXXXXX or 254XXXXXXXXX
    r"|0([7][0-9]{8})"    # 07XXXXXXXX
    r"|0([1][0-9]{8})"    # 01XXXXXXXX (Airtel/Telkom short form)
    r")$"
)


def normalize_phone(raw: str) -> str:
    """Normalise a Kenyan phone number to 254XXXXXXXXX.

    Accepts:
        07XXXXXXXX  → 2547XXXXXXXX
        01XXXXXXXX  → 2541XXXXXXXX
        +254XXXXXXX → 254XXXXXXXXX
        254XXXXXXXX → 254XXXXXXXXX

    Raises ValueError for invalid formats.
    """
    cleaned = re.sub(r"[\s\-]", "", raw.strip())
    m = KENYAN_PHONE_RE.match(cleaned)
    if not m:
        raise ValueError(
            "Invalid Kenyan phone number. "
            "Use 07XX XXX XXX, 01XX XXX XXX, or +254XXXXXXXXX."
        )
    local = m.group(1) or m.group(2) or m.group(3)
    return f"254{local}"


# ---------------------------------------------------------------------------
# Order creation
# ---------------------------------------------------------------------------


def create_order_from_cart(
    cart: Cart,
    customer_name: str,
    phone: str,
    delivery_zone: DeliveryZone,
    delivery_address: str,
    email: str = "",
    notes: str = "",
) -> Order:
    """Create an Order and its OrderItems from the current cart.

    Computes all totals server-side. Does NOT reduce stock here — stock
    is only reduced after successful M-Pesa callback.

    Raises ValueError if the cart is empty.
    """
    if cart.is_empty():
        raise ValueError("Cannot create an order from an empty cart.")

    subtotal = cart.subtotal
    delivery_fee = delivery_zone.fee
    total = subtotal + delivery_fee

    with transaction.atomic():
        order = Order.objects.create(
            customer_name=customer_name,
            phone=phone,
            email=email,
            delivery_zone=delivery_zone,
            delivery_address=delivery_address,
            delivery_fee=delivery_fee,
            subtotal=subtotal,
            total=total,
            notes=notes,
        )

        for item in cart:
            # Refresh price from DB — never trust session price alone
            try:
                product = Product.objects.get(pk=item["product_id"], is_active=True)
            except Product.DoesNotExist:
                continue  # product deactivated between add and checkout
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_price=product.price,
                quantity=item["quantity"],
            )

    return order
