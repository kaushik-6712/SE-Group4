from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.shortcuts import render

from .forms import SORT_CHOICES, SORT_ORDERING, SearchForm
from .models import Category, Product, Variant, sort_sizes

PAGE_SIZE = 12


def home(request):
    """Landing page: banner, categories and the newest products."""
    new_arrivals = (
        Product.objects.filter(active=True)
        .select_related("category")
        .prefetch_related("variants")
        .order_by("-created_at", "pk")[:8]
    )
    return render(request, "catalog/home.html", {
        "categories": Category.objects.all(),
        "new_arrivals": new_arrivals,
    })


def product_list(request):
    """Use Case 2: browse by category, search by keyword, filter, sort and paginate."""
    products = Product.objects.filter(active=True).select_related("category").prefetch_related("variants")
    form = SearchForm(request.GET or None)
    form_errors = []
    selected_category = None
    keyword = ""
    ordering = SORT_ORDERING["newest"]
    page_number = 1

    if form.is_bound:
        if form.is_valid():
            data = form.cleaned_data
            keyword = data.get("q") or ""
            if keyword:
                products = products.filter(
                    Q(name__icontains=keyword) | Q(description__icontains=keyword) | Q(brand__icontains=keyword)
                )
            if data.get("category"):
                selected_category = data["category"]
                products = products.filter(category=selected_category)
            if data.get("size"):
                products = products.filter(variants__size=data["size"])
            if data.get("color"):
                products = products.filter(variants__color__iexact=data["color"])
            if data.get("min_price") is not None:
                products = products.filter(price__gte=data["min_price"])
            if data.get("max_price") is not None:
                products = products.filter(price__lte=data["max_price"])
            ordering = SORT_ORDERING[data.get("sort") or "newest"]
            page_number = data.get("page") or 1
        else:
            form_errors = [error for errors in form.errors.values() for error in errors]

    products = products.order_by(*ordering).distinct()
    paginator = Paginator(products, PAGE_SIZE)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        form_errors.append(f"Page {page_number} does not exist.")
        page_obj = paginator.page(1)

    active_variants = Variant.objects.filter(product__active=True)
    context = {
        "page_obj": page_obj,
        "result_count": paginator.count,
        "categories": Category.objects.all(),
        "sizes": sort_sizes(active_variants.values_list("size", flat=True)),
        "colors": sorted(set(active_variants.values_list("color", flat=True))),
        "sort_choices": SORT_CHOICES,
        "form_errors": form_errors,
        "selected_category": selected_category,
        "keyword": keyword,
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, pk):
    """Use Case 3: product page with sizes, colors and stock per variant."""
    product = (
        Product.objects.select_related("category").prefetch_related("variants").filter(pk=pk).first()
    )
    if product is None or not product.active:
        return render(request, "catalog/unavailable.html", status=404)

    variants = list(product.variants.all())
    size_rank = {size: i for i, size in enumerate(sort_sizes(v.size for v in variants))}
    colors = product.color_list()
    variants.sort(key=lambda v: (colors.index(v.color), size_rank[v.size]))
    related = (
        Product.objects.filter(active=True, category=product.category)
        .exclude(pk=product.pk)
        .prefetch_related("variants")
        .order_by("-created_at")[:4]
    )
    context = {
        "product": product,
        "related": related,
        "sizes": sort_sizes(v.size for v in variants),
        "colors": colors,
        "variants": variants,
        "variants_json": [
            {"id": v.pk, "size": v.size, "color": v.color, "stock": v.stock_qty} for v in variants
        ],
    }
    return render(request, "catalog/product_detail.html", context)
