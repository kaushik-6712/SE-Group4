from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalog.models import Product

from .services import CartError, add_item, calculate_subtotal, get_cart, remove_item, resolve_variant, update_quantity


@login_required
def cart_detail(request):
    cart = get_cart(request.user)
    items = list(cart.items.select_related("variant__product__category"))
    rows = []
    has_blocking_issue = False
    for item in items:
        notes = item.notes()
        has_blocking_issue = has_blocking_issue or any(blocking for _, blocking in notes)
        rows.append({"item": item, "notes": notes})

    # A price-change notice is shown once, then the new price is accepted.
    for item in items:
        if item.price_at_add != item.variant.product.price:
            item.price_at_add = item.variant.product.price
            item.save(update_fields=["price_at_add"])

    context = {
        "rows": rows,
        "subtotal": calculate_subtotal(items),
        "has_blocking_issue": has_blocking_issue,
    }
    return render(request, "cart/cart_detail.html", context)


@require_POST
def add_to_cart(request):
    product_id = request.POST.get("product_id", "")
    product_url = (
        reverse("catalog:detail", args=[int(product_id)]) if product_id.isdigit() else reverse("catalog:list")
    )
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to add items to your cart.")
        return redirect(f"{reverse('accounts:login')}?{urlencode({'next': product_url})}")

    try:
        variant = resolve_variant(
            product_id,
            request.POST.get("size", "").strip(),
            request.POST.get("color", "").strip(),
        )
        add_item(request.user, variant.pk, request.POST.get("quantity", "1"))
    except CartError as exc:
        messages.error(request, str(exc))
        if product_id.isdigit() and Product.objects.filter(pk=int(product_id), active=True).exists():
            return redirect(product_url)
        return redirect("catalog:list")

    messages.success(request, "Item added to cart.")
    return redirect("cart:detail")


@login_required
@require_POST
def update_item(request, item_id):
    try:
        update_quantity(request.user, item_id, request.POST.get("quantity"))
        messages.success(request, "Cart updated.")
    except CartError as exc:
        messages.error(request, str(exc))
    return redirect("cart:detail")


@login_required
@require_POST
def remove_cart_item(request, item_id):
    try:
        remove_item(request.user, item_id)
        messages.success(request, "Item removed from cart.")
    except CartError as exc:
        messages.error(request, str(exc))
    return redirect("cart:detail")
