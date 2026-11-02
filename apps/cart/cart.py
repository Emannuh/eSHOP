"""
Session-based shopping cart.

Cart data is stored in the Django session as:
{
    "<product_id>": {
        "quantity": <int>,
        "price": <int KES>,   # snapshot at add time
        "name": <str>,
    },
    ...
}

Prices are always integers (KES). All totals are computed server-side.
"""
from __future__ import annotations

from collections.abc import Iterator

from django.http import HttpRequest

from apps.catalog.models import Product

CART_SESSION_KEY = "cart"


class Cart:
    """Thin wrapper around the session for cart operations."""

    def __init__(self, request: HttpRequest) -> None:
        self.session = request.session
        cart = self.session.get(CART_SESSION_KEY)
        if cart is None:
            cart = {}
            self.session[CART_SESSION_KEY] = cart
        self._cart: dict[str, dict] = cart

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Mark session as modified so Django persists it."""
        self.session.modified = True

    def add(self, product: Product, quantity: int = 1) -> None:
        """Add a product or increase its quantity.

        Respects available stock — will not exceed Product.stock.
        """
        key = str(product.pk)
        if key not in self._cart:
            self._cart[key] = {
                "quantity": 0,
                "price": product.price,
                "name": product.name,
            }
        new_qty = self._cart[key]["quantity"] + quantity
        # Cap at available stock
        self._cart[key]["quantity"] = min(new_qty, product.stock)
        self._save()

    def update(self, product_id: int, quantity: int) -> None:
        """Set an item's quantity directly.  quantity=0 removes the item."""
        key = str(product_id)
        if key not in self._cart:
            return
        if quantity <= 0:
            self.remove(product_id)
            return
        self._cart[key]["quantity"] = quantity
        self._save()

    def remove(self, product_id: int) -> None:
        """Remove an item from the cart."""
        key = str(product_id)
        if key in self._cart:
            del self._cart[key]
            self._save()

    def clear(self) -> None:
        """Empty the entire cart (called after a successful order)."""
        self.session[CART_SESSION_KEY] = {}
        self._cart = self.session[CART_SESSION_KEY]
        self._save()

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[dict]:
        """Yield enriched cart item dicts with subtotal included."""
        for product_id, item in self._cart.items():
            yield {
                "product_id": int(product_id),
                "name": item["name"],
                "price": item["price"],
                "quantity": item["quantity"],
                "subtotal": item["price"] * item["quantity"],
            }

    def __len__(self) -> int:
        """Total number of individual items (sum of quantities)."""
        return sum(item["quantity"] for item in self._cart.values())

    def is_empty(self) -> bool:
        return len(self._cart) == 0

    @property
    def subtotal(self) -> int:
        """Sum of (price × quantity) for all items, in KES."""
        return sum(item["price"] * item["quantity"] for item in self._cart.values())

    def get_item(self, product_id: int) -> dict | None:
        return self._cart.get(str(product_id))
