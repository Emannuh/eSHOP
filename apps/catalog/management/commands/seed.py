"""
Seed management command.

Creates sample categories, products, and delivery zones for local dev.

Usage:
    python manage.py seed
    python manage.py seed --clear   # wipe existing data first
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.catalog.models import Category, Product
from apps.orders.models import DeliveryZone

CATEGORIES = [
    {"name": "Electronics", "description": "Phones, laptops, accessories"},
    {"name": "Fashion", "description": "Clothing, shoes, bags"},
    {"name": "Home & Kitchen", "description": "Appliances, cookware, decor"},
    {"name": "Health & Beauty", "description": "Skincare, supplements, personal care"},
    {"name": "Sports & Outdoors", "description": "Fitness gear, camping, bicycles"},
]

PRODUCTS = [
    # Electronics
    {"name": "Samsung Galaxy A35 5G", "category": "Electronics", "price": 29999, "stock": 15,
     "description": "6.6\" AMOLED, 128GB, 5G connectivity, 50MP camera"},
    {"name": "Tecno Spark 20 Pro", "category": "Electronics", "price": 16999, "stock": 20,
     "description": "6.6\" display, 256GB, 32MP selfie camera"},
    {"name": "Apple AirPods Pro 2nd Gen", "category": "Electronics", "price": 24999, "stock": 8,
     "description": "Active noise cancellation, spatial audio"},
    {"name": "Anker 65W USB-C Charger", "category": "Electronics", "price": 2999, "stock": 30,
     "description": "GaN technology, ultra-compact, fast charging"},
    # Fashion
    {"name": "Men's Casual Linen Shirt", "category": "Fashion", "price": 1899, "stock": 40,
     "description": "Breathable linen, available in blue/white/khaki"},
    {"name": "Women's Ankara Wrap Dress", "category": "Fashion", "price": 2499, "stock": 25,
     "description": "Vibrant kitenge print, one-size adjustable wrap"},
    {"name": "Leather Sandals (Akala)", "category": "Fashion", "price": 1299, "stock": 50,
     "description": "Handcrafted genuine leather, Nairobi-made"},
    # Home & Kitchen
    {"name": "Ramtons 20L Microwave", "category": "Home & Kitchen", "price": 8999, "stock": 10,
     "description": "700W, 5 power levels, timer function"},
    {"name": "Non-Stick Cooking Set (5pc)", "category": "Home & Kitchen", "price": 3499, "stock": 18,
     "description": "PFOA-free, induction compatible, includes lids"},
    # Health & Beauty
    {"name": "Amara Shea Butter Cream", "category": "Health & Beauty", "price": 650, "stock": 60,
     "description": "100% pure shea butter, unscented, 250ml"},
    {"name": "Protein Powder (1kg)", "category": "Health & Beauty", "price": 4999, "stock": 12,
     "description": "Whey protein isolate, chocolate flavor, 30 servings"},
    # Sports
    {"name": "Yoga Mat with Strap", "category": "Sports & Outdoors", "price": 1799, "stock": 35,
     "description": "6mm thick, non-slip, includes carry strap"},
    {"name": "Jump Rope (Speed)", "category": "Sports & Outdoors", "price": 699, "stock": 50,
     "description": "Ball-bearing handles, adjustable cable"},
]

DELIVERY_ZONES = [
    {"name": "Nairobi CBD", "fee": 150},
    {"name": "Westlands / Kilimani", "fee": 200},
    {"name": "Thika Road (Roysambu – Thika)", "fee": 250},
    {"name": "Mombasa Road (South B – Athi River)", "fee": 300},
    {"name": "Ngong Road / Karen / Lang'ata", "fee": 250},
    {"name": "Eastlands (Umoja, Kayole, Komarock)", "fee": 200},
    {"name": "Outside Nairobi", "fee": 500},
]


class Command(BaseCommand):
    help = "Seed the database with sample categories, products, and delivery zones."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing catalog and delivery zone data before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data…")
            Product.objects.all().delete()
            Category.objects.all().delete()
            DeliveryZone.objects.all().delete()

        # Create categories
        category_map: dict[str, Category] = {}
        for cat_data in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                slug=slugify(cat_data["name"]),
                defaults={**cat_data},
            )
            category_map[cat_data["name"]] = cat
            verb = "Created" if created else "Exists"
            self.stdout.write(f"  {verb} category: {cat.name}")

        # Create products
        for p_data in PRODUCTS:
            cat_name = p_data.pop("category")
            cat = category_map[cat_name]
            slug = slugify(p_data["name"])
            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={"category": cat, **p_data},
            )
            verb = "Created" if created else "Exists"
            self.stdout.write(f"  {verb} product: {product.name}")
            p_data["category"] = cat_name  # restore for idempotency

        # Create delivery zones
        for zone_data in DELIVERY_ZONES:
            zone, created = DeliveryZone.objects.get_or_create(
                name=zone_data["name"],
                defaults={"fee": zone_data["fee"]},
            )
            verb = "Created" if created else "Exists"
            self.stdout.write(f"  {verb} zone: {zone.name} — KES {zone.fee}")

        self.stdout.write(self.style.SUCCESS("\nSeed complete."))
