"""Catalog views: home, category, product detail, search."""
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Category, Product


def home(request: HttpRequest) -> HttpResponse:
    """Landing page: featured categories and latest products."""
    categories = Category.objects.filter(is_active=True, parent=None).prefetch_related(
        "children"
    )[:6]
    featured_products = Product.objects.filter(is_active=True, stock__gt=0).select_related(
        "category"
    ).prefetch_related("images")[:8]
    return render(
        request,
        "catalog/home.html",
        {"categories": categories, "featured_products": featured_products},
    )


def category_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """List products in a category with pagination."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    # Include sub-category products
    category_ids = [category.pk] + list(
        category.children.values_list("pk", flat=True)
    )
    products_qs: QuerySet = (
        Product.objects.filter(
            category__in=category_ids, is_active=True
        )
        .select_related("category")
        .prefetch_related("images")
    )
    paginator = Paginator(products_qs, 12)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "catalog/category.html",
        {"category": category, "page_obj": page},
    )


def product_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Product detail page."""
    product = get_object_or_404(
        Product.objects.prefetch_related("images").select_related("category"),
        slug=slug,
        is_active=True,
    )
    related = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=product.pk).prefetch_related("images")[:4]
    return render(
        request,
        "catalog/product_detail.html",
        {"product": product, "related": related},
    )


def search(request: HttpRequest) -> HttpResponse:
    """Full-text search across product name and description."""
    query = request.GET.get("q", "").strip()
    products_qs: QuerySet = Product.objects.none()
    if query:
        products_qs = (
            Product.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query),
                is_active=True,
            )
            .select_related("category")
            .prefetch_related("images")
        )
    paginator = Paginator(products_qs, 12)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "catalog/search.html",
        {"query": query, "page_obj": page},
    )
