from django.contrib import admin

from .models import Sale, SaleItem, StockMovement


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = (
        "product",
        "product_name_snapshot",
        "barcode_snapshot",
        "quantity",
        "unit_price",
        "gst_rate_snapshot",
        "taxable_amount",
        "tax_amount",
        "line_total",
    )
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("bill_number", "created_at", "item_count", "grand_total", "status")
    list_filter = ("status", "pricing_mode_snapshot")
    search_fields = ("bill_number",)
    inlines = [SaleItemInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity_change", "reason", "created_at")
    list_filter = ("reason",)
    search_fields = ("product__name",)
