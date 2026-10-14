"""Product inventory models."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


def normalize_barcode(value):
    """Trim surrounding whitespace and collapse blanks to ``None``.

    A blank barcode must be stored as ``NULL`` so that multiple products
    without a barcode can coexist under the unique constraint.
    """
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def search(self, term):
        term = (term or "").strip()
        if not term:
            return self
        return self.filter(Q(name__icontains=term) | Q(barcode__iexact=term))


class Product(models.Model):
    """A sellable item in the shop catalogue."""

    name = models.CharField(max_length=200)
    barcode = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Optional. Must be unique when present.",
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="GST percentage, e.g. 18 for 18%.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["barcode"], name="product_barcode_idx"),
            models.Index(fields=["name"], name="product_name_idx"),
            models.Index(fields=["is_active"], name="product_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(selling_price__gte=0), name="product_price_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(stock_quantity__gte=0),
                name="product_stock_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(gst_rate__gte=0) & Q(gst_rate__lte=100),
                name="product_gst_rate_range",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.barcode = normalize_barcode(self.barcode)
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    @property
    def is_out_of_stock(self) -> bool:
        return self.stock_quantity <= 0

    @property
    def is_low_stock(self) -> bool:
        from apps.core.models import ShopSettings

        threshold = ShopSettings.get_solo().low_stock_threshold
        return 0 < self.stock_quantity <= threshold

    @property
    def stock_status(self) -> str:
        if self.is_out_of_stock:
            return "out"
        if self.is_low_stock:
            return "low"
        return "ok"
