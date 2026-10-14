"""Template context available to every page."""

from .models import ShopSettings


def shop_context(request):
    shop = ShopSettings.get_solo()
    return {
        "shop": shop,
        "currency_symbol": shop.currency_symbol,
        "low_stock_threshold": shop.low_stock_threshold,
    }
