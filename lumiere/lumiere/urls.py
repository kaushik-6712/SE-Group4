from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Lumiere Administration"
admin.site.site_title = "Lumiere Admin"
admin.site.index_title = "Catalog, inventory and orders"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("cart/", include("cart.urls")),
    path("orders/", include("orders.urls")),
    path("", include("catalog.urls")),
]

# Serve uploaded product photos while developing (DEBUG=True).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
