"""Use Case 1 – Register / Log In. Mirrors Table 3 in the Testing section."""
from django.test import TestCase
from django.urls import reverse

from .models import User

VALID = {
    "name": "Saija Sagi",
    "email": "saija@gmail.com",
    "password": "Lumiere2026",
    "confirm_password": "Lumiere2026",
}


class RegisterTests(TestCase):
    def register(self, **overrides):
        data = {**VALID, **overrides}
        return self.client.post(reverse("accounts:register"), data)

    # name
    def test_name_empty_invalid(self):
        response = self.register(name="")
        self.assertFormError(response.context["form"], "name", "Name is required.")
        self.assertFalse(User.objects.exists())

    def test_name_digits_only_invalid(self):
        response = self.register(name="12345")
        self.assertFormError(response.context["form"], "name", "Name must contain letters.")

    def test_name_too_long_invalid(self):
        response = self.register(name="A" * 121)
        self.assertFormError(response.context["form"], "name", "Name must be 120 characters or fewer.")

    def test_name_valid(self):
        response = self.register()
        self.assertRedirects(response, reverse("catalog:home"))
        self.assertEqual(User.objects.get().name, "Saija Sagi")

    # email
    def test_email_missing_at_invalid(self):
        response = self.register(email="saija.gmail.com")
        self.assertFormError(response.context["form"], "email", "Enter a valid email address.")

    def test_email_missing_domain_invalid(self):
        response = self.register(email="saija@")
        self.assertFormError(response.context["form"], "email", "Enter a valid email address.")

    def test_email_already_registered_invalid(self):
        User.objects.create_user("john@gmail.com", "Lumiere2026", name="John")
        response = self.register(email="john@gmail.com")
        self.assertFormError(
            response.context["form"], "email", "Email already in use. Please log in or use a different email."
        )

    def test_email_valid(self):
        self.register(email="Saija@Gmail.com")
        self.assertTrue(User.objects.filter(email="saija@gmail.com").exists())

    # password
    def test_password_too_short_invalid(self):
        response = self.register(password="abc12", confirm_password="abc12")
        self.assertIn("too short", " ".join(response.context["form"].errors["password"]))

    def test_password_letters_only_invalid(self):
        response = self.register(password="lumierestore", confirm_password="lumierestore")
        self.assertIn("Password must contain both letters and digits.", response.context["form"].errors["password"])

    def test_password_digits_only_invalid(self):
        response = self.register(password="84736251", confirm_password="84736251")
        self.assertFalse(User.objects.exists())

    def test_password_mismatch_invalid(self):
        response = self.register(confirm_password="Lumiere2027")
        self.assertFormError(response.context["form"], "confirm_password", "Passwords do not match.")

    def test_password_valid_is_hashed(self):
        self.register()
        user = User.objects.get()
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(user.check_password("Lumiere2026"))
        self.assertEqual(user.role, User.Role.CUSTOMER)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("john@gmail.com", "Lumiere2026", name="John")

    def login(self, email="john@gmail.com", password="Lumiere2026"):
        return self.client.post(reverse("accounts:login"), {"email": email, "password": password})

    def test_valid_login(self):
        response = self.login()
        self.assertRedirects(response, reverse("catalog:home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_email_empty_invalid(self):
        response = self.login(email="")
        self.assertFormError(response.context["form"], "email", "Email is required.")

    def test_wrong_password_generic_message(self):
        response = self.login(password="Wrong1234")
        self.assertContains(response, "Invalid email or password.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_attempts, 1)

    def test_unknown_email_same_generic_message(self):
        response = self.login(email="nobody@gmail.com")
        self.assertContains(response, "Invalid email or password.")

    def test_failed_attempts_below_limit_valid(self):
        self.login(password="Wrong1234")
        response = self.login()
        self.assertRedirects(response, reverse("catalog:home"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_attempts, 0)

    def test_failed_attempts_limit_reached_locks_login(self):
        for _ in range(User.MAX_FAILED_ATTEMPTS):
            self.login(password="Wrong1234")
        response = self.login()  # correct password, but the account is locked
        self.assertContains(response, "Too many failed attempts")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_customer_cannot_open_admin(self):
        self.client.force_login(self.user)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_administrator_can_open_admin(self):
        admin = User.objects.create_superuser("admin@lumiere.com", "Admin2026pass")
        self.assertTrue(admin.is_staff)
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
