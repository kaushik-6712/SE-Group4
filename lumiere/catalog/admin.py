from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, Recommendation, Variant


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1
    fields = ("size", "color", "stock_qty")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Use Case 8: manage the product catalog."""

    list_display = ("thumbnail", "name", "category", "brand", "price", "active", "stock_total", "updated_at")
    list_display_links = ("thumbnail", "name")
    readonly_fields = ("preview",)
    fields = ("name", "category", "brand", "price", "description", "image", "preview", "active")
    list_filter = ("active", "category", "brand")
    search_fields = ("name", "brand", "description")
    inlines = [VariantInline]
    actions = ["deactivate_products", "activate_products"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").prefetch_related("variants")

    @admin.display(description="Photo")
    def thumbnail(self, obj):
        return format_html('<img src="{}" alt="" style="width:44px;height:55px;object-fit:cover;border-radius:4px">', obj.image_url)

    @admin.display(description="Current photo")
    def preview(self, obj):
        if not obj.pk:
            return "-"
        return format_html('<img src="{}" alt="" style="width:160px;border-radius:6px">', obj.image_url)

    @admin.display(description="Total stock")
    def stock_total(self, obj):
        return obj.total_stock()

    @admin.action(description="Deactivate selected products (hide from customers)")
    def deactivate_products(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f"{updated} product(s) deactivated.")

    @admin.action(description="Activate selected products")
    def activate_products(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f"{updated} product(s) activated.")


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    """Use Case 9: manage inventory per size and color."""

    list_display = ("product", "size", "color", "stock_qty", "stock_status")
    list_editable = ("stock_qty",)
    list_filter = ("product__category", "size", "color")
    search_fields = ("product__name",)
    list_select_related = ("product",)

    @admin.display(description="Status")
    def stock_status(self, obj):
        return "In stock" if obj.stock_qty > 0 else "Out of stock"


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("product", "customer", "score", "created_at")
    list_select_related = ("product", "customer")
