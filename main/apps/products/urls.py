from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("new/", views.product_create, name="create"),
    path("<int:pk>/edit/", views.product_edit, name="edit"),
    path("<int:pk>/stock/", views.product_stock, name="stock"),
    path("<int:pk>/toggle/", views.product_toggle_active, name="toggle"),
]
