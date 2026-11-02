"""Checkout form for order creation."""
from django import forms

from .models import DeliveryZone
from .services import normalize_phone


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=200,
        label="Full Name",
        widget=forms.TextInput(attrs={"placeholder": "Jane Wanjiru", "autocomplete": "name"}),
    )
    phone = forms.CharField(
        max_length=15,
        label="M-Pesa Phone Number",
        widget=forms.TextInput(
            attrs={"placeholder": "07XX XXX XXX", "autocomplete": "tel"}
        ),
        help_text="The number you will use to pay. Format: 07XX, 01XX, or +254XX",
    )
    email = forms.EmailField(
        required=False,
        label="Email (optional)",
        widget=forms.EmailInput(attrs={"placeholder": "jane@example.com", "autocomplete": "email"}),
    )
    delivery_zone = forms.ModelChoiceField(
        queryset=DeliveryZone.objects.filter(is_active=True),
        label="Delivery Area",
        empty_label="— Select your area —",
    )
    delivery_address = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Street / building / apartment…"}),
        label="Delivery Address",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Any special instructions…"}),
        label="Notes (optional)",
    )

    def clean_phone(self) -> str:
        phone = self.cleaned_data["phone"]
        try:
            return normalize_phone(phone)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
