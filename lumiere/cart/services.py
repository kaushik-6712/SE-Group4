"""Business rules for the shopping cart (Use Case 4)."""
from decimal import Decimal

from django.db import transaction

from catalog.models import Product, Variant

from .models import Cart, CartItem


class CartError(Exception):
    """A cart action was rejected; the message is shown to the customer."""


def get_cart(customer):
    cart, _ = Cart.objects.get_or_create(customer=customer)
    return cart


def _parse_quantity(quantity):
    try:
        value = int(str(quantity).strip())
    except (TypeError, ValueError):
        raise CartError("Quantity must be a whole number.")
    if value < 1:
        raise CartError("Quantity must be at least 1.")
    return value


def resolve_variant(product_id, size, color):
    """Turn the size and color chosen on the product page into a Variant."""
    if not size:
        raise CartError("Please select a size.")
    if not color:
        raise CartError("Please select a color.")
    try:
        product = Product.objects.get(pk=int(product_id), active=True)
    except (Product.DoesNotExist, TypeError, ValueError):
        raise CartError("This product is no longer available.")

    variants = list(product.variants.all())
    if size not in {v.size for v in variants}:
        raise CartError(f"Size {size} is not offered for this product.")
    if color not in {v.color for v in variants}:
        raise CartError(f"Color {color} is not offered for this product.")
    for variant in variants:
        if variant.size == size and variant.color == color:
            return variant
    raise CartError(f"{size} / {color} is not offered for this product.")


def add_item(customer, variant_id, quantity):
    """Add a variant to the cart, merging with an existing line for the same variant."""
    quantity = _parse_quantity(quantity)
    with transaction.atomic():
        try:
            variant = Variant.objects.select_related("product").get(pk=int(variant_id))
        except (Variant.DoesNotExist, TypeError, ValueError):
            raise CartError("This item is not available.")
        if not variant.product.active:
            raise CartError("This product is no longer available.")
        if variant.stock_qty == 0:
            raise CartError("This size and color is out of stock.")

        cart = get_cart(customer)
        item = CartItem.objects.filter(cart=cart, variant=variant).first()
        already = item.quantity if item else 0
        if already + quantity > variant.stock_qty:
            message = f"Only {variant.stock_qty} available in this size."
            if already:
                message += f" You already have {already} in your cart."
            raise CartError(message)

        if item:
            item.quantity = already + quantity
            item.price_at_add = variant.product.price
            item.save(update_fields=["quantity", "price_at_add"])
        else:
            item = CartItem.objects.create(
                cart=cart, variant=variant, quantity=quantity, price_at_add=variant.product.price
            )
    return item


def _get_own_item(customer, item_id):
    try:
        return CartItem.objects.select_related("variant__product").get(pk=int(item_id), cart__customer=customer)
    except (CartItem.DoesNotExist, TypeError, ValueError):
        raise CartError("That item is not in your cart.")


def update_quantity(customer, item_id, quantity):
    item = _get_own_item(customer, item_id)
    quantity = _parse_quantity(quantity)
    if quantity > item.variant.stock_qty:
        raise CartError(f"Only {item.variant.stock_qty} available in this size.")
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item


def remove_item(customer, item_id):
    item = _get_own_item(customer, item_id)
    item.delete()


def calculate_subtotal(items):
    return sum((item.line_total for item in items), Decimal("0.00"))
