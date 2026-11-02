"""URL patterns for the orders app."""
from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("<int:pk>/waiting/", views.order_waiting, name="waiting"),
    path("<int:pk>/status/", views.order_status, name="status"),
    path("<int:pk>/confirmation/", views.order_confirmation, name="confirmation"),
]
