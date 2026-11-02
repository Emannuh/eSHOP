"""URL patterns for the payments app."""
from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("callback/", views.mpesa_callback, name="callback"),
]
