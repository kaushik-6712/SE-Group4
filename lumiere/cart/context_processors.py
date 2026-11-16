from django.db.models import Sum

from .models import CartItem


def cart_count(request):
    """Number of items in the logged-in customer's cart, shown in the header."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"cart_count": 0}
    total = CartItem.objects.filter(cart__customer=user).aggregate(n=Sum("quantity"))["n"]
    return {"cart_count": total or 0}
