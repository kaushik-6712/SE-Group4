from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import redirect, render

from cart.services import calculate_subtotal, get_cart
from payments.gateway import TEST_PAYMENT_METHODS

from .forms import AddressForm
from .models import Order
from .services import CheckoutError, place_order


@login_required
def checkout(request):
    """Use Case 5: shipping address + payment, then place the order."""
    cart = get_cart(request.user)
    items = list(cart.items.select_related("variant__product__category"))
    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect("cart:detail")

    addresses = list(request.user.addresses.order_by("-created_at"))
    default_choice = str(addresses[0].pk) if addresses else "new"
    address_choice = request.POST.get("address_choice", default_choice)
    payment_method = request.POST.get("payment_method", "pm_card_visa")
    address_form = AddressForm(request.POST if request.method == "POST" and address_choice == "new" else None)

    if request.method == "POST":
        address = None
        if address_choice == "new":
            if address_form.is_valid():
                address = address_form.save(commit=False)  # saved inside the checkout transaction
        else:
            address = next((a for a in addresses if str(a.pk) == address_choice), None)
            if address is None:
                messages.error(request, "Please choose a shipping address.")

        if payment_method not in TEST_PAYMENT_METHODS:
            messages.error(request, "Please choose a payment method.")
            address = None

        if address is not None:
            try:
                order = place_order(request.user, address, payment_method)
            except CheckoutError as exc:
                messages.error(request, str(exc))
            else:
                return redirect("orders:confirmation", pk=order.pk)

    context = {
        "items": items,
        "subtotal": calculate_subtotal(items),
        "addresses": addresses,
        "address_choice": address_choice,
        "address_form": address_form,
        "payment_methods": TEST_PAYMENT_METHODS.items(),
        "payment_method": payment_method,
    }
    return render(request, "orders/checkout.html", context)


def _get_own_order(request, pk):
    order = (
        Order.objects.select_related("address", "customer")
        .prefetch_related("items__variant__product", "payments")
        .filter(pk=pk)
        .first()
    )
    if order is None:
        raise Http404("Order not found")
    if order.customer_id != request.user.pk:
        return None
    return order


@login_required
def confirmation(request, pk):
    order = _get_own_order(request, pk)
    if order is None:
        return render(request, "orders/access_denied.html", status=403)
    return render(request, "orders/confirmation.html", {"order": order})


@login_required
def order_history(request):
    """Use Case 6: the customer's own orders, newest first."""
    orders = request.user.orders.annotate(item_count=Sum("items__quantity")).order_by("-created_at", "-pk")
    return render(request, "orders/order_history.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = _get_own_order(request, pk)
    if order is None:
        return render(request, "orders/access_denied.html", status=403)
    return render(request, "orders/order_detail.html", {"order": order})
