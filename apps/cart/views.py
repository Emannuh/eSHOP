"""
Cart views — all mutations return HTMX-friendly partial responses.

Endpoints:
    GET  /cart/              → full cart page
    POST /cart/add/<pk>/     → add item (HTMX)
    POST /cart/update/<pk>/  → update quantity (HTMX)
    POST /cart/remove/<pk>/  → remove item (HTMX)
"""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Product

from .cart import Cart


def cart_detail(request: HttpRequest) -> HttpResponse:
    """Full cart page."""
    cart = Cart(request)
    return render(request, "cart/cart.html", {"cart": cart})


@require_POST
def cart_add(request: HttpRequest, pk: int) -> HttpResponse:
    """Add a product to the cart.  Supports HTMX."""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    qty = int(request.POST.get("quantity", 1))
    cart = Cart(request)
    cart.add(product, quantity=qty)

    if request.htmx:
        return render(request, "partials/cart_icon.html", {"cart": cart})
    from django.shortcuts import redirect
    return redirect("cart:detail")


@require_POST
def cart_update(request: HttpRequest, pk: int) -> HttpResponse:
    """Update item quantity.  Supports HTMX."""
    qty = int(request.POST.get("quantity", 1))
    cart = Cart(request)
    cart.update(pk, qty)

    if request.htmx:
        return render(request, "partials/cart_items.html", {"cart": cart})
    from django.shortcuts import redirect
    return redirect("cart:detail")


@require_POST
def cart_remove(request: HttpRequest, pk: int) -> HttpResponse:
    """Remove an item from the cart.  Supports HTMX."""
    cart = Cart(request)
    cart.remove(pk)

    if request.htmx:
        return render(request, "partials/cart_items.html", {"cart": cart})
    from django.shortcuts import redirect
    return redirect("cart:detail")
