"""
Catalog models: Category, Product, ProductImage.

Prices are stored as integers (KES) to avoid floating-point money bugs.
"""
import os

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


def validate_image(image: object) -> None:
    """Validate uploaded image size and type."""

    max_size_mb = 5
    if hasattr(image, "size") and image.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Image must be smaller than {max_size_mb} MB.")


def product_image_upload_path(instance: "ProductImage", filename: str) -> str:
    """Store product images under media/products/<slug>/."""
    ext = os.path.splitext(filename)[1].lower()
    slug = instance.product.slug if instance.product_id else "unknown"
    return f"products/{slug}/{instance.product_id}{ext}"


def category_image_upload_path(instance: "Category", filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return f"categories/{instance.slug}{ext}"


class Category(models.Model):
    """A product category that can be nested one level deep."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to=category_image_upload_path,
        blank=True,
        null=True,
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self) -> str:
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("catalog:category", kwargs={"slug": self.slug})


class Product(models.Model):
    """A product in the store."""

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    # Price in KES as integer — no floating-point money bugs
    price = models.PositiveIntegerField(help_text="Price in KES (integer)")
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "category"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("catalog:product", kwargs={"slug": self.slug})

    @property
    def primary_image(self) -> "ProductImage | None":
        """Return the primary image or the first image available."""
        return (
            self.images.filter(is_primary=True).first()
            or self.images.first()
        )

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @property
    def price_display(self) -> str:
        """KES 1,500 formatted string."""
        return f"KES {self.price:,}"


class ProductImage(models.Model):
    """Additional images for a product."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to=product_image_upload_path,
    )
    alt_text = models.CharField(max_length=200, blank=True)
    ordering = models.PositiveSmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["ordering", "id"]

    def __str__(self) -> str:
        return f"{self.product.name} — image {self.id}"

    def save(self, *args, **kwargs) -> None:
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
