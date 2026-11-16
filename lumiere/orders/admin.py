from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import Order, OrderItem, Payment
from .services import StatusError, update_status


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "size", "color", "quantity", "unit_price")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    fields = ("provider", "provider_reference", "status", "amount", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status"]

    def clean_status(self):
        new = self.cleaned_data["status"]
        old = Order.objects.get(pk=self.instance.pk).status
        if new != old and not Order.transition_allowed(old, new):
            raise ValidationError(
                f"Invalid status change: {Order.Status(old).label} → {Order.Status(new).label}."
            )
        return new


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Use Case 10: review orders and move them through fulfillment."""

    form = OrderAdminForm
    list_display = ("order_number", "customer", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer__email", "customer__name", "id")
    date_hierarchy = "created_at"
    fields = ("order_number", "customer", "address", "total", "created_at", "status")
    readonly_fields = ("order_number", "customer", "address", "total", "created_at")
    inlines = [OrderItemInline, PaymentInline]
    actions = ["mark_processing", "mark_shipped", "mark_delivered", "cancel_orders"]
    list_select_related = ("customer",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Order", ordering="id")
    def order_number(self, obj):
        return obj.order_number

    def save_model(self, request, obj, form, change):
        if change and "status" in form.changed_data:
            update_status(Order.objects.get(pk=obj.pk), obj.status)

    def _apply(self, request, queryset, status):
        updated = 0
        for order in queryset:
            try:
                update_status(order, status)
                updated += 1
            except StatusError as exc:
                self.message_user(request, f"{order.order_number}: {exc}", level=messages.ERROR)
        if updated:
            self.message_user(
                request, f"{updated} order(s) set to {Order.Status(status).label}.", level=messages.SUCCESS
            )

    @admin.action(description="Mark selected orders as Processing")
    def mark_processing(self, request, queryset):
        self._apply(request, queryset, Order.Status.PROCESSING)

    @admin.action(description="Mark selected orders as Shipped")
    def mark_shipped(self, request, queryset):
        self._apply(request, queryset, Order.Status.SHIPPED)

    @admin.action(description="Mark selected orders as Delivered")
    def mark_delivered(self, request, queryset):
        self._apply(request, queryset, Order.Status.DELIVERED)

    @admin.action(description="Cancel selected orders (restores stock)")
    def cancel_orders(self, request, queryset):
        self._apply(request, queryset, Order.Status.CANCELLED)
