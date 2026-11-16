import re

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class RegisterForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        error_messages={
            "required": "Name is required.",
            "max_length": "Name must be 120 characters or fewer.",
        },
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        max_length=255,
        error_messages={"required": "Email is required.", "invalid": "Enter a valid email address."},
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password = forms.CharField(
        error_messages={"required": "Password is required."},
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 8 characters, with letters and digits.",
    )
    confirm_password = forms.CharField(
        label="Confirm password",
        error_messages={"required": "Please confirm your password."},
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not re.search(r"[A-Za-z]", name):
            raise ValidationError("Name must contain letters.")
        return name

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email already in use. Please log in or use a different email.")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)
        if password and confirm and password != confirm:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned


class LoginForm(forms.Form):
    email = forms.EmailField(
        error_messages={"required": "Email is required.", "invalid": "Enter a valid email address."},
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password = forms.CharField(
        error_messages={"required": "Password is required."},
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
