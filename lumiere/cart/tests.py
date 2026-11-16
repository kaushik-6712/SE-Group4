"""Use Case 4 – Manage Shopping Cart."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from catalog.models import Category, Product, Variant

from .models import CartItem
from .services import CartError, add_item, update_quantity


class AddToCartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("saija@gmail.com", "Lumiere2026", name="Saija")
        category = Category.objects.create(name="T-Shirts", slug="t-shirts")
        self.product = Product.objects.create(
            category=category, name="Essential Crew Tee", description="Cotton tee", brand="Lumiere Basics",
            price=Decimal("22.00"),
        )
        self.medium = Variant.objects.create(product=self.product, size="M", color="Black", stock_qty=3)
        self.large = Variant.objects.create(product=self.product, size="L", color="Black", stock_qty=0)
        self.inactive = Product.objects.create(
            category=category, name="Archive Tee", description="Old", brand="Lumiere Basics",
            price=Decimal("18.00"), active=False,
        )
        Variant.objects.create(product=self.inactive, size="M", color="White", stock_qty=5)
        self.client.force_login(self.user)

    def add(self, follow=True, **overrides):
        data = {"product_id": self.product.pk, "size": "M", "color": "Black", "quantity": "2", **overrides}
        return self.client.post(reverse("cart:add"), data, follow=follow)

    def test_valid_add(self):
        response = self.add()
        self.assertContains(response, "Item added to cart.")
        item = CartItem.objects.get()
        self.assertEqual((item.variant, item.quantity), (self.medium, 2))

    def test_quantity_exceeds_stock_invalid(self):
        response = self.add(quantity="8")
        self.assertContains(response, "Only 3 available in this size.")
        self.assertFalse(CartItem.objects.exists())

    def test_quantity_zero_invalid(self):
        response = self.add(quantity="0")
        self.assertContains(response, "Quantity must be at least 1.")

    def test_quantity_negative_invalid(self):
        response = self.add(quantity="-1")
        self.assertContains(response, "Quantity must be at least 1.")

    def test_quantity_text_invalid(self):
        response = self.add(quantity="two")
        self.assertContains(response, "Quantity must be a whole number.")

    def test_repeated_add_merges_into_one_line(self):
        self.add(quantity="1")
        self.add(quantity="1")
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.get().quantity, 2)

    def test_merge_cannot_exceed_stock(self):
        self.add(quantity="2")
        response = self.add(quantity="2")
        self.assertContains(response, "You already have 2 in your cart.")
        self.assertEqual(CartItem.objects.get().quantity, 2)

    def test_size_empty_invalid(self):
        response = self.add(size="")
        self.assertContains(response, "Please select a size.")

    def test_size_not_offered_invalid(self):
        response = self.add(size="XXXL")
        self.assertContains(response, "Size XXXL is not offered for this product.")

    def test_color_not_offered_invalid(self):
        response = self.add(color="Purple")
        self.assertContains(response, "Color Purple is not offered for this product.")

    def test_out_of_stock_variant_invalid(self):
        response = self.add(size="L")
        self.assertContains(response, "This size and color is out of stock.")

    def test_inactive_product_invalid(self):
        response = self.add(product_id=self.inactive.pk, color="White")
        self.assertContains(response, "This product is no longer available.")

    def test_not_logged_in_redirects_to_login(self):
        self.client.logout()
        response = self.add(follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("accounts:login")))

    def test_variant_id_zero_invalid(self):
        with self.assertRaisesMessage(CartError, "This item is not available."):
            add_item(self.user, 0, 1)

    def test_update_quantity_valid_and_invalid(self):
        item = add_item(self.user, self.medium.pk, 1)
        update_quantity(self.user, item.pk, 3)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
        with self.assertRaisesMessage(CartError, "Only 3 available in this size."):
            update_quantity(self.user, item.pk, 4)

    def test_remove_item(self):
        item = add_item(self.user, self.medium.pk, 1)
        self.client.post(reverse("cart:remove", args=[item.pk]))
        self.assertFalse(CartItem.objects.exists())

    def test_cannot_change_another_customers_item(self):
        other = User.objects.create_user("other@gmail.com", "Lumiere2026", name="Other")
        item = add_item(other, self.medium.pk, 1)
        with self.assertRaisesMessage(CartError, "That item is not in your cart."):
            update_quantity(self.user, item.pk, 2)

    def test_cart_page_shows_subtotal_and_price_change(self):
        add_item(self.user, self.medium.pk, 2)
        self.product.price = Decimal("25.00")
        self.product.save()
        response = self.client.get(reverse("cart:detail"))
        self.assertContains(response, "$50.00")
        self.assertContains(response, "Price changed from $22.00 to $25.00.")
