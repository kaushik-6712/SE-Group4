from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from catalog.models import Variant


class Cart(models.Model):
    # OneToOne + UNIQUE: a customer has at most one cart (1 : 0..1).
    customer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"

    def __str__(self):
        return f"Cart of {self.customer.email}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField()
    price_at_add = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "cart_items"
        ordering = ["added_at", "pk"]
        constraints = [
            # Repeated additions of the same variant merge into one cart line.
            models.UniqueConstraint(fields=["cart", "variant"], name="unique_cart_variant"),
            models.CheckConstraint(check=Q(quantity__gte=1), name="cart_item_quantity_min_1"),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.variant}"

    @property
    def unit_price(self):
        return self.variant.product.price

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def notes(self):
        """Messages to show on the cart page: (text, blocks_checkout)."""
        product = self.variant.product
        notes = []
        if not product.active:
            notes.append(("This item is no longer available. Please remove it.", True))
        elif self.variant.stock_qty == 0:
            notes.append(("This size and color is now out of stock. Please remove it.", True))
        elif self.quantity > self.variant.stock_qty:
            notes.append(
                (f"Only {self.variant.stock_qty} available in this size. Please reduce the quantity.", True)
            )
        if self.price_at_add != product.price:
            notes.append((f"Price changed from ${self.price_at_add} to ${product.price}.", False))
        return notes
