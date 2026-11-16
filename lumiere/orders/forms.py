import re

from django import forms
from django.core.exceptions import ValidationError

from accounts.models import Address

COUNTRY_CHOICES = [("", "Select country"), ("United States", "United States")]


class AddressForm(forms.ModelForm):
    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        error_messages={
            "required": "Country is required.",
            "invalid_choice": "We currently ship only within the United States.",
        },
    )

    class Meta:
        model = Address
        fields = ["street", "city", "state", "postal_code", "country"]
        labels = {"street": "Street address", "postal_code": "ZIP code"}
        error_messages = {
            "street": {
                "required": "Street address is required.",
                "max_length": "Street address must be 255 characters or fewer.",
            },
            "city": {"required": "City is required."},
            "state": {"required": "State is required."},
            "postal_code": {"required": "ZIP code is required."},
        }

    def clean_street(self):
        return " ".join(self.cleaned_data["street"].split())

    def clean_city(self):
        city = " ".join(self.cleaned_data["city"].split())
        if not re.search(r"[A-Za-z]", city):
            raise ValidationError("City must contain letters.")
        return city

    def clean_postal_code(self):
        code = self.cleaned_data["postal_code"].strip()
        if not re.fullmatch(r"\d{5}(-\d{4})?", code):
            raise ValidationError("Enter a valid 5-digit ZIP code.")
        return code
