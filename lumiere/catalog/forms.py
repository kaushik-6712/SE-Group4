from django import forms
from django.core.exceptions import ValidationError

from .models import Category

SORT_CHOICES = [
    ("newest", "Newest"),
    ("price_asc", "Price: low to high"),
    ("price_desc", "Price: high to low"),
]

SORT_ORDERING = {
    "newest": ("-created_at", "pk"),
    "price_asc": ("price", "pk"),
    "price_desc": ("-price", "pk"),
}


class SearchForm(forms.Form):
    """Validates every browse/search input before it reaches the database."""

    q = forms.CharField(
        required=False,
        max_length=100,
        error_messages={"max_length": "Search keyword must be 100 characters or fewer."},
    )
    category = forms.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "Category must be a number.",
            "min_value": "Select a valid category.",
        },
    )
    size = forms.CharField(required=False, max_length=30)
    color = forms.CharField(required=False, max_length=40)
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        error_messages={
            "invalid": "Minimum price must be a number.",
            "min_value": "Minimum price cannot be negative.",
        },
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        error_messages={
            "invalid": "Maximum price must be a number.",
            "min_value": "Maximum price cannot be negative.",
        },
    )
    sort = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        error_messages={"invalid_choice": "Unknown sort option."},
    )
    page = forms.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "Page must be a number.",
            "min_value": "Page number must be 1 or greater.",
        },
    )

    def clean_q(self):
        return " ".join(self.cleaned_data["q"].split())

    def clean_category(self):
        value = self.cleaned_data["category"]
        if value is None:
            return None
        try:
            return Category.objects.get(pk=value)
        except Category.DoesNotExist:
            raise ValidationError("Category does not exist.")

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_price"), cleaned.get("max_price")
        if low is not None and high is not None and high < low:
            raise ValidationError("Invalid price range: the minimum price is greater than the maximum price.")
        return cleaned
