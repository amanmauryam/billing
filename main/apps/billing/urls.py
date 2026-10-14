from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("pos/", views.pos_view, name="pos"),
    path("pos/search/", views.product_search, name="product_search"),
    path("pos/lookup/", views.barcode_lookup, name="barcode_lookup"),
    path("pos/checkout/", views.checkout, name="checkout"),
    path("sales/", views.sale_list, name="sale_list"),
    path("sales/<str:bill_number>/", views.sale_detail, name="sale_detail"),
]
