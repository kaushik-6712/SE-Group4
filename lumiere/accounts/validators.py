import re

from django.core.exceptions import ValidationError


class LettersAndDigitsValidator:
    """Reject weak passwords that are only letters or only digits."""

    def validate(self, password, user=None):
        if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
            raise ValidationError(
                "Password must contain both letters and digits.",
                code="password_weak",
            )

    def get_help_text(self):
        return "Your password must contain both letters and digits."
