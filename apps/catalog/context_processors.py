"""Inject navigation categories into every template context."""
from django.http import HttpRequest

from .models import Category


def nav_categories(request: HttpRequest) -> dict:
    """Add top-level active categories to the global template context."""
    categories = Category.objects.filter(is_active=True, parent=None)[:8]
    return {"nav_categories": categories}
