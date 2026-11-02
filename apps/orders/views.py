"""
Orders views: checkout, order confirmation, status poll.
"""
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from apps.cart.cart import Cart

from .forms import CheckoutForm
from .models import Order
from .services import create_order_from_cart


@never_cache
def checkout(request: HttpRequest) -> HttpResponse:
    """Show and process the checkout form."""
    cart = Cart(request)
    if cart.is_empty():
        messages.warning(request, "Your cart is empty.")
        return redirect("catalog:home")

    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        order = create_order_from_cart(
            cart=cart,
            customer_name=form.cleaned_data["customer_name"],
            phone=form.cleaned_data["phone"],
            email=form.cleaned_data.get("email", ""),
            delivery_zone=form.cleaned_data["delivery_zone"],
            delivery_address=form.cleaned_data["delivery_address"],
            notes=form.cleaned_data.get("notes", ""),
        )
        # Trigger STK Push
        from apps.payments.services import DarajaService

        service = DarajaService()
        result = service.stk_push(
            phone=order.phone,
            amount=order.total,
            order=order,
        )
        if result.get("success"):
            cart.clear()
            return redirect("orders:waiting", pk=order.pk)
        else:
            messages.error(
                request,
                f"Could not initiate payment: {result.get('error', 'Unknown error')}",
            )

    return render(
        request,
        "orders/checkout.html",
        {"form": form, "cart": cart},
    )


@never_cache
def order_waiting(request: HttpRequest, pk: int) -> HttpResponse:
    """'Check your phone' waiting page — HTMX polls /orders/<pk>/status/ every 3s."""
    order = get_object_or_404(Order, pk=pk)
    return render(request, "orders/waiting.html", {"order": order})


@never_cache
def order_status(request: HttpRequest, pk: int) -> HttpResponse:
    """HTMX polling endpoint — returns a small HTML fragment."""
    order = get_object_or_404(Order, pk=pk)
    return render(request, "partials/order_status.html", {"order": order})


@never_cache
def order_confirmation(request: HttpRequest, pk: int) -> HttpResponse:
    """Success/failure confirmation page."""
    order = get_object_or_404(Order, pk=pk)
    return render(request, "orders/confirmation.html", {"order": order})
