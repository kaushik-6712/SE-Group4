from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="detail"),
    path("add/", views.add_to_cart, name="add"),
    path("items/<int:item_id>/update/", views.update_item, name="update"),
    path("items/<int:item_id>/remove/", views.remove_cart_item, name="remove"),
]
