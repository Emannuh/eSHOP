"""Tests for session cart logic."""
import pytest

from apps.cart.cart import Cart


class FakeSession(dict):
    """Minimal session dict that supports the .modified attribute."""

    def __init__(self):
        super().__init__()
        self.modified = False


@pytest.fixture
def mock_request(rf):
    """A fake request with a session that supports .modified."""
    request = rf.get("/")
    request.session = FakeSession()
    return request


@pytest.fixture
def product(db):
    from apps.catalog.models import Category, Product

    cat = Category.objects.create(name="Electronics", slug="electronics")
    return Product.objects.create(
        category=cat,
        name="Test Phone",
        slug="test-phone",
        price=10000,
        stock=5,
    )


def test_empty_cart(mock_request):
    cart = Cart(mock_request)
    assert len(cart) == 0
    assert cart.subtotal == 0
    assert cart.is_empty()


def test_add_item(mock_request, product):
    cart = Cart(mock_request)
    cart.add(product, quantity=2)
    assert len(cart) == 2
    assert cart.subtotal == 20000


def test_add_item_respects_stock(mock_request, product):
    cart = Cart(mock_request)
    cart.add(product, quantity=100)  # stock is 5
    assert len(cart) == 5


def test_update_item(mock_request, product):
    cart = Cart(mock_request)
    cart.add(product, quantity=2)
    cart.update(product.pk, 4)
    assert len(cart) == 4
    assert cart.subtotal == 40000


def test_remove_item(mock_request, product):
    cart = Cart(mock_request)
    cart.add(product)
    cart.remove(product.pk)
    assert cart.is_empty()


def test_update_zero_removes_item(mock_request, product):
    cart = Cart(mock_request)
    cart.add(product)
    cart.update(product.pk, 0)
    assert cart.is_empty()


def test_clear(mock_request, product):
    cart = Cart(mock_request)
    cart.add(product)
    cart.clear()
    assert cart.is_empty()


def test_subtotal_multiple_items(mock_request, db):
    from apps.catalog.models import Category, Product

    cat = Category.objects.create(name="Fashion", slug="fashion")
    p1 = Product.objects.create(category=cat, name="Shirt", slug="shirt", price=1000, stock=10)
    p2 = Product.objects.create(category=cat, name="Dress", slug="dress", price=2000, stock=10)

    cart = Cart(mock_request)
    cart.add(p1, quantity=2)  # 2000
    cart.add(p2, quantity=3)  # 6000
    assert cart.subtotal == 8000
