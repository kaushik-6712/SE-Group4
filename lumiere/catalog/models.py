from django.conf import settings
from django.db import models
from django.db.models import Q
from django.templatetags.static import static
from django.utils import timezone

SIZE_ORDER = ["XXS", "XS", "S", "M", "L", "XL", "XXL"]


def sort_sizes(sizes):
    """Order letter sizes XS..XXL, then numeric sizes (28, 30, ...)."""

    def key(size):
        if size in SIZE_ORDER:
            return (0, SIZE_ORDER.index(size), "")
        if size.isdigit():
            return (1, int(size), "")
        return (2, 0, size)

    return sorted(set(sizes), key=key)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        db_table = "categories"
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200)
    description = models.TextField()
    brand = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="products/", blank=True, help_text="Product photo (portrait, about 4:5).")
    active = models.BooleanField(default=True, help_text="Inactive products are hidden from customers.")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["category", "active"], name="product_category_active_idx")]
        constraints = [
            models.CheckConstraint(check=Q(price__gt=0), name="product_price_positive"),
        ]

    def __str__(self):
        return self.name

    @property
    def image_url(self):
        """The uploaded photo, or a neutral placeholder when there is none."""
        return self.image.url if self.image else static("img/placeholder.svg")

    # These helpers read prefetched variants, so list pages stay at a fixed query count.
    def color_list(self):
        """Colors in the order they were added, so the first one matches the photo."""
        ordered = sorted(self.variants.all(), key=lambda v: v.pk)
        return list(dict.fromkeys(v.color for v in ordered))

    def in_stock(self):
        return any(v.stock_qty > 0 for v in self.variants.all())

    def total_stock(self):
        return sum(v.stock_qty for v in self.variants.all())


class Variant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size = models.CharField(max_length=30)
    color = models.CharField(max_length=40)
    stock_qty = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "variants"
        ordering = ["product", "color", "size"]
        constraints = [
            models.UniqueConstraint(fields=["product", "size", "color"], name="unique_product_size_color"),
            models.CheckConstraint(check=Q(stock_qty__gte=0), name="variant_stock_non_negative"),
        ]

    def __str__(self):
        return f"{self.product.name} – {self.size} / {self.color}"

    def is_in_stock(self, quantity=1):
        return self.product.active and self.stock_qty >= quantity


class Recommendation(models.Model):
    """Scored product suggestions. customer is NULL for general (non-personal) picks."""

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recommendations",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="recommendations")
    score = models.DecimalField(max_digits=6, decimal_places=4)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "recommendations"
        ordering = ["-score"]

    def __str__(self):
        who = self.customer.email if self.customer else "general"
        return f"{self.product.name} for {who} ({self.score})"
