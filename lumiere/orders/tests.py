"""Use Cases 5, 6 and 10 – Checkout, order history and order status."""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Address, User
from cart.models import CartItem
from cart.services import add_item
from catalog.models import Category, Product, Variant

from .models import Order, Payment
from .services import CheckoutError, StatusError, place_order, update_status

NEW_ADDRESS = {
    "address_choice": "new",
    "street": "8000 York Rd",
    "city": "Towson",
    "state": "MD",
    "postal_code": "21252",
    "country": "United States",
    "payment_method": "pm_card_visa",
}


@override_settings(PAYMENT_MODE="mock")
class CheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("saija@gmail.com", "Lumiere2026", name="Saija")
        category = Category.objects.create(name="Jackets", slug="jackets")
        self.product = Product.objects.create(
            category=category, name="Denim Trucker Jacket", description="Denim", brand="Atelier North",
            price=Decimal("50.00"),
        )
        self.variant = Variant.objects.create(product=self.product, size="M", color="Indigo", stock_qty=5)
        add_item(self.user, self.variant.pk, 2)
        self.client.force_login(self.user)

    def checkout(self, **overrides):
        return self.client.post(reverse("orders:checkout"), {**NEW_ADDRESS, **overrides})

    def test_successful_checkout(self):
        response = self.checkout()
        order = Order.objects.get()
        self.assertRedirects(response, reverse("orders:confirmation", args=[order.pk]))
        self.assertEqual(order.total, Decimal("100.00"))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.get().unit_price, Decimal("50.00"))
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 3)
        self.assertFalse(CartItem.objects.exists())
        payment = Payment.objects.get()
        self.assertEqual(payment.status, "SUCCEEDED")
        self.assertTrue(payment.provider_reference.startswith("mock_pi_"))

    def test_declined_payment_leaves_no_partial_order(self):
        response = self.checkout(payment_method="pm_card_chargeDeclined")
        self.assertContains(response, "Payment declined")
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(Address.objects.exists())  # rolled back with the transaction
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 5)
        self.assertEqual(CartItem.objects.get().quantity, 2)

    def test_insufficient_funds_declined(self):
        response = self.checkout(payment_method="pm_card_chargeDeclinedInsufficientFunds")
        self.assertContains(response, "insufficient funds")
        self.assertFalse(Order.objects.exists())

    def test_unknown_payment_method_invalid(self):
        response = self.checkout(payment_method="4111111111111111")
        self.assertContains(response, "Please choose a payment method.")
        self.assertFalse(Order.objects.exists())

    def test_empty_cart_blocked(self):
        CartItem.objects.all().delete()
        response = self.checkout()
        self.assertRedirects(response, reverse("cart:detail"))
        self.assertFalse(Order.objects.exists())

    def test_stock_changed_since_added(self):
        self.variant.stock_qty = 1
        self.variant.save()
        response = self.checkout()
        self.assertContains(response, "An item in your cart has changed.")
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartItem.objects.get().quantity, 2)

    def test_not_logged_in_redirects(self):
        self.client.logout()
        response = self.checkout()
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_street_empty_invalid(self):
        response = self.checkout(street="")
        self.assertFormError(response.context["address_form"], "street", "Street address is required.")
        self.assertFalse(Order.objects.exists())

    def test_street_too_long_invalid(self):
        response = self.checkout(street="A" * 256)
        self.assertFormError(
            response.context["address_form"], "street", "Street address must be 255 characters or fewer."
        )

    def test_city_digits_invalid(self):
        response = self.checkout(city="12345")
        self.assertFormError(response.context["address_form"], "city", "City must contain letters.")

    def test_postal_code_wrong_format_invalid(self):
        for code in ["AB12", "2125"]:
            response = self.checkout(postal_code=code)
            self.assertFormError(response.context["address_form"], "postal_code", "Enter a valid 5-digit ZIP code.")
        self.assertFalse(Order.objects.exists())

    def test_country_unsupported_invalid(self):
        response = self.checkout(country="Canada")
        self.assertFormError(
            response.context["address_form"], "country", "We currently ship only within the United States."
        )

    def test_saved_address_can_be_reused(self):
        address = Address.objects.create(
            customer=self.user, street="1 Main St", city="Towson", state="MD", postal_code="21204",
            country="United States",
        )
        response = self.checkout(address_choice=str(address.pk), street="", city="", postal_code="")
        order = Order.objects.get()
        self.assertEqual(order.address, address)
        self.assertRedirects(response, reverse("orders:confirmation", args=[order.pk]))


@override_settings(PAYMENT_MODE="mock")
class OrderHistoryAndStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("saija@gmail.com", "Lumiere2026", name="Saija")
        self.other = User.objects.create_user("tony@gmail.com", "Lumiere2026", name="Tony")
        category = Category.objects.create(name="Knitwear", slug="knitwear")
        product = Product.objects.create(
            category=category, name="Merino Crew Sweater", description="Merino", brand="Atelier North",
            price=Decimal("88.00"),
        )
        self.variant = Variant.objects.create(product=product, size="L", color="Navy", stock_qty=4)
        add_item(self.user, self.variant.pk, 1)
        address = Address(street="8000 York Rd", city="Towson", state="MD", postal_code="21252", country="United States")
        self.order = place_order(self.user, address, "pm_card_visa")

    def test_history_lists_own_orders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("orders:history"))
        self.assertContains(response, self.order.order_number)

    def test_history_empty_message(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("orders:history"))
        self.assertContains(response, "No orders placed yet")

    def test_other_customer_order_access_denied(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("orders:detail", args=[self.order.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Access denied", status_code=403)

    def test_valid_status_flow(self):
        for status in ["PROCESSING", "SHIPPED", "DELIVERED"]:
            update_status(self.order, status)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "DELIVERED")

    def test_invalid_status_change_rejected(self):
        update_status(self.order, "PROCESSING")
        update_status(self.order, "SHIPPED")
        update_status(self.order, "DELIVERED")
        with self.assertRaisesMessage(StatusError, "Cannot change status from Delivered to Pending."):
            update_status(self.order, "PENDING")

    def test_cancel_restores_stock(self):
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 3)
        update_status(self.order, "CANCELLED")
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 4)

    def test_cannot_cancel_shipped_order(self):
        update_status(self.order, "PROCESSING")
        update_status(self.order, "SHIPPED")
        with self.assertRaises(StatusError):
            update_status(self.order, "CANCELLED")

    def test_place_order_with_empty_cart_raises(self):
        address = Address(street="8000 York Rd", city="Towson", state="MD", postal_code="21252", country="United States")
        with self.assertRaisesMessage(CheckoutError, "Your cart is empty."):
            place_order(self.user, address, "pm_card_visa")

    def test_admin_status_change_validates_transitions(self):
        admin = User.objects.create_superuser("admin@lumiere.com", "Admin2026pass")
        self.client.force_login(admin)
        url = reverse("admin:orders_order_change", args=[self.order.pk])
        response = self.client.post(url, {
            "status": "DELIVERED",
            "items-TOTAL_FORMS": "1", "items-INITIAL_FORMS": "1", "items-MIN_NUM_FORMS": "0", "items-MAX_NUM_FORMS": "1000",
            "items-0-id": str(self.order.items.get().pk), "items-0-order": str(self.order.pk),
            "payments-TOTAL_FORMS": "1", "payments-INITIAL_FORMS": "1", "payments-MIN_NUM_FORMS": "0", "payments-MAX_NUM_FORMS": "1000",
            "payments-0-id": str(self.order.payments.get().pk), "payments-0-order": str(self.order.pk),
        })
        self.assertContains(response, "Invalid status change: Pending → Delivered.")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PENDING")
