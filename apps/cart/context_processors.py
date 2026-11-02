"""Make the cart available in every template."""
from django.http import HttpRequest

from .cart import Cart


def cart(request: HttpRequest) -> dict:
    """Inject cart into every template context."""
    return {"cart": Cart(request)}
