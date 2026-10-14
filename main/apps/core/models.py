"""Core configuration models for the Offline Shop POS."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class ShopSettings(models.Model):
    """A single configuration record describing the shop.

    Exactly one row should exist. Use :meth:`get_solo` to fetch (creating a
    default row on first use) and always save through that instance so the
    singleton invariant is enforced at the application level.
    """

    RECEIPT_WIDTH_58 = "58"
    RECEIPT_WIDTH_80 = "80"
    RECEIPT_WIDTH_CHOICES = [
        (RECEIPT_WIDTH_58, "58mm"),
        (RECEIPT_WIDTH_80, "80mm"),
    ]

    PRICING_INCLUSIVE = "inclusive"
    PRICING_EXCLUSIVE = "exclusive"
    PRICING_MODE_CHOICES = [
        (PRICING_INCLUSIVE, "GST-inclusive (tax included in selling price)"),
        (PRICING_EXCLUSIVE, "GST-exclusive (tax added to selling price)"),
    ]

    shop_name = models.CharField(max_length=150, default="My Shop")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    gstin = models.CharField(
        "GSTIN / Tax registration",
        max_length=40,
        blank=True,
        help_text="Optional. Shown on receipts only if you enter it.",
    )
    state = models.CharField(
        "Shop state",
        max_length=80,
        blank=True,
        help_text="Optional. Used only if CGST/SGST splitting is enabled.",
    )
    receipt_width = models.CharField(
        max_length=2, choices=RECEIPT_WIDTH_CHOICES, default=RECEIPT_WIDTH_58
    )
    pricing_mode = models.CharField(
        max_length=10, choices=PRICING_MODE_CHOICES, default=PRICING_INCLUSIVE
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=5, validators=[MinValueValidator(0)]
    )
    receipt_footer = models.TextField(
        blank=True, default="Thank you for your business!"
    )
    is_configured = models.BooleanField(
        default=False,
        help_text="Set once the first-run setup has been completed.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Shop settings"
        verbose_name_plural = "Shop settings"

    def __str__(self) -> str:
        return self.shop_name

    def save(self, *args, **kwargs):
        # Force a single row with a stable primary key.
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - guard rail
        raise RuntimeError("Shop settings cannot be deleted; edit them instead.")

    @classmethod
    def get_solo(cls) -> "ShopSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def currency_symbol(self) -> str:
        return "\u20b9"

    @property
    def receipt_width_mm(self) -> str:
        return f"{self.receipt_width}mm"
