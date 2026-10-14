"""Root URL configuration for the Offline Shop POS."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("products/", include("apps.products.urls")),
    path("", include("apps.billing.urls")),
]
