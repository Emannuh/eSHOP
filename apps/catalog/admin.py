"""Admin configuration for the catalog app."""
import csv
from typing import Any

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "ordering", "image_preview")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj: ProductImage) -> str:
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px; max-width:120px;" />',
                obj.image.url,
            )
        return "—"

    image_preview.short_description = "Preview"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active",)


def export_products_csv(modeladmin: Any, request: Any, queryset: Any) -> HttpResponse:
    """Export selected products as CSV."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="products.csv"'
    writer = csv.writer(response)
    writer.writerow(["ID", "Name", "Category", "Price (KES)", "Stock", "Active"])
    for p in queryset.select_related("category"):
        writer.writerow([p.pk, p.name, p.category.name, p.price, p.stock, p.is_active])
    return response


export_products_csv.short_description = "Export selected products as CSV"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price_display",
        "stock",
        "is_active",
        "primary_image_preview",
        "created_at",
    )
    list_filter = ("is_active", "category", "created_at")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active", "stock")
    inlines = [ProductImageInline]
    actions = [export_products_csv]
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("category", "name", "slug", "description")}),
        ("Pricing & Stock", {"fields": ("price", "stock", "is_active")}),
        ("SEO", {"fields": ("meta_title", "meta_description")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def price_display(self, obj: Product) -> str:
        return obj.price_display

    price_display.short_description = "Price"
    price_display.admin_order_field = "price"

    def primary_image_preview(self, obj: Product) -> str:
        img = obj.primary_image
        if img:
            return format_html(
                '<img src="{}" style="max-height:60px; max-width:90px;" />',
                img.image.url,
            )
        return "—"

    primary_image_preview.short_description = "Image"
