"""Tests for order creation service."""
import pytest

from apps.cart.cart import Cart
from apps.orders.models import Order, OrderItem
from apps.orders.services import create_order_from_cart


@pytest.fixture
def zone(db):
    from apps.orders.models import DeliveryZone

    return DeliveryZone.objects.create(name="CBD", fee=150)


@pytest.fixture
def product(db):
    from apps.catalog.models import Category, Product

    cat = Category.objects.create(name="Electronics", slug="electronics-orders")
    return Product.objects.create(
        category=cat, name="Laptop", slug="laptop", price=50000, stock=3
    )


class FakeSession(dict):
    modified = False


@pytest.fixture
def mock_request(rf):
    request = rf.get("/")
    request.session = FakeSession()
    return request


def test_create_order_from_cart(mock_request, product, zone):
    cart = Cart(mock_request)
    cart.add(product, quantity=2)

    order = create_order_from_cart(
        cart=cart,
        customer_name="Jane Wanjiru",
        phone="254712345678",
        email="jane@example.com",
        delivery_zone=zone,
        delivery_address="Westlands, Nairobi",
    )

    assert order.pk is not None
    assert order.subtotal == 100000
    assert order.delivery_fee == 150
    assert order.total == 100150
    assert order.status == Order.Status.PENDING
    assert order.reference.startswith("DKA-")
    assert OrderItem.objects.filter(order=order).count() == 1


def test_order_item_price_snapshot(mock_request, product, zone):
    """Price in the OrderItem must reflect the price at checkout, not future changes."""
    cart = Cart(mock_request)
    cart.add(product, quantity=1)

    order = create_order_from_cart(
        cart=cart,
        customer_name="Test",
        phone="254712345678",
        delivery_zone=zone,
        delivery_address="CBD",
    )
    item = order.items.first()
    assert item.product_price == 50000  # snapshot of price at checkout

    # Change the price after the fact
    product.price = 99999
    product.save()

    # Snapshot should be unchanged
    item.refresh_from_db()
    assert item.product_price == 50000


def test_empty_cart_raises(mock_request, zone):
    cart = Cart(mock_request)
    with pytest.raises(ValueError, match="empty"):
        create_order_from_cart(
            cart=cart,
            customer_name="Nobody",
            phone="254712345678",
            delivery_zone=zone,
            delivery_address="Nowhere",
        )
