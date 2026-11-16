from .models import Category


def nav_categories(request):
    """Categories for the header menu and the footer."""
    return {"nav_categories": Category.objects.all()}
