"""Business rules for checkout and order fulfillment (Use Cases 5 and 10)."""
from decimal import Decimal

from django.db import transaction

from cart.models import Cart
from catalog.models import Variant
from payments.gateway import submit_payment

from .models import Order, OrderItem, Payment


class CheckoutError(Exception):
    """Checkout was rejected; nothing was saved and the cart is unchanged."""


class StatusError(Exception):
    """An invalid order status change was attempted."""


def place_order(customer, address, payment_method):
    """
    Convert the customer's cart into a paid order.

    Everything runs in one database transaction: stock is re-checked under a row
    lock, payment is requested, and only on success are the order, order items
    and payment record created, stock reduced and the cart cleared. Any failure
    raises CheckoutError and rolls the whole transaction back, so no partial
    order or incorrect stock change is ever saved.
    """
    cart = Cart.objects.filter(customer=customer).first()
    items = list(cart.items.select_related("variant__product")) if cart else []
    if not items:
        raise CheckoutError("Your cart is empty.")

    with transaction.atomic():
        # Lock the variant rows so two customers cannot buy the last unit at once.
        locked = {
            v.pk: v
            for v in Variant.objects.select_for_update()
            .select_related("product")
            .filter(pk__in=[item.variant_id for item in items])
        }

        problems = []
        total = Decimal("0.00")
        for item in items:
            variant = locked[item.variant_id]
            if not variant.product.active:
                problems.append(f"{variant.product.name} is no longer available.")
            elif item.quantity > variant.stock_qty:
                problems.append(
                    f"Only {variant.stock_qty} of {variant.product.name} ({variant.size} / {variant.color}) left in stock."
                )
            total += variant.product.price * item.quantity
        if problems:
            raise CheckoutError("An item in your cart has changed. " + " ".join(problems))

        if address.pk is None:
            address.customer = customer
            address.save()

        result = submit_payment(total, payment_method, description=f"Lumiere order for {customer.email}")
        if not result.success:
            raise CheckoutError(result.message or "Payment failed.")

        order = Order.objects.create(customer=customer, address=address, total=total)
        for item in items:
            variant = locked[item.variant_id]
            OrderItem.objects.create(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                size=variant.size,
                color=variant.color,
                quantity=item.quantity,
                unit_price=variant.product.price,
            )
            variant.stock_qty -= item.quantity
            variant.save(update_fields=["stock_qty"])

        Payment.objects.create(
            order=order,
            provider=result.provider,
            provider_reference=result.reference,
            status=result.status,
            amount=total,
        )
        cart.items.all().delete()

    return order


def update_status(order, new_status):
    """Apply a fulfillment status change; cancelling restores stock."""
    if new_status not in Order.Status.values:
        raise StatusError("Unknown order status.")

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        old_status = order.status
        if not Order.transition_allowed(old_status, new_status):
            raise StatusError(
                f"Cannot change status from {Order.Status(old_status).label} to {Order.Status(new_status).label}."
            )

        if new_status == Order.Status.CANCELLED:
            items = list(order.items.all())
            variants = {
                v.pk: v
                for v in Variant.objects.select_for_update().filter(pk__in=[i.variant_id for i in items])
            }
            for item in items:
                variant = variants[item.variant_id]
                variant.stock_qty += item.quantity
                variant.save(update_fields=["stock_qty"])

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
    return order


def cancel_order(order):
    return update_status(order, Order.Status.CANCELLED)
