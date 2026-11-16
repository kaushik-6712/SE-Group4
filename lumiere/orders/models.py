from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.models import Address
from catalog.models import Variant


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    # Valid fulfillment transitions (Use Case 10). Anything else is rejected.
    ALLOWED_TRANSITIONS = {
        Status.PENDING: {Status.PROCESSING, Status.CANCELLED},
        Status.PROCESSING: {Status.SHIPPED, Status.CANCELLED},
        Status.SHIPPED: {Status.DELIVERED},
        Status.DELIVERED: set(),
        Status.CANCELLED: set(),
    }

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["customer", "created_at"], name="order_customer_created_idx")]

    def __str__(self):
        return self.order_number

    @property
    def order_number(self):
        return f"LUM-{self.pk:06d}" if self.pk else "LUM-new"

    @classmethod
    def transition_allowed(cls, old, new):
        return new in cls.ALLOWED_TRANSITIONS.get(old, set())

    @property
    def latest_payment(self):
        payments = list(self.payments.all())
        return payments[-1] if payments else None


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    # PROTECT: a variant (and so its product) that appears in past orders cannot be deleted.
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT, related_name="order_items")
    product_name = models.CharField(max_length=200)
    size = models.CharField(max_length=30)
    color = models.CharField(max_length=40)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # price snapshot at purchase

    class Meta:
        db_table = "order_items"
        ordering = ["pk"]
        constraints = [models.CheckConstraint(check=Q(quantity__gte=1), name="order_item_quantity_min_1")]

    def __str__(self):
        return f"{self.quantity} × {self.product_name} ({self.size}/{self.color})"

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=20)
    provider_reference = models.CharField(max_length=150)
    status = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "payments"
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"{self.provider_reference} ({self.status})"
