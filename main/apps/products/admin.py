from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "barcode",
        "selling_price",
        "gst_rate",
        "stock_quantity",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "barcode")
