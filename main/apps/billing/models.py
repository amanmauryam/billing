"""Billing, sale snapshot, and stock movement models."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.core.models import ShopSettings
from apps.products.models import Product


class SaleQuerySet(models.QuerySet):
    def completed(self):
        return self.filter(status=Sale.STATUS_COMPLETED)


class Sale(models.Model):
    """A completed sales invoice.

    Amounts are split deliberately:

    * ``subtotal``      - sum of ``quantity x unit_price`` as entered.
    * ``taxable_total`` - sum of line taxable amounts (net of GST).
    * ``tax_total``     - total GST.
    * ``grand_total``   - amount payable (tax-inclusive gross).

    For GST-exclusive pricing ``subtotal == taxable_total``; for
    GST-inclusive pricing ``subtotal == grand_total``.
    """

    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [(STATUS_COMPLETED, "Completed")]

    PAYMENT_CASH = "cash"
    PAYMENT_UPI = "upi"
    PAYMENT_CREDIT = "credit"
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_UPI, "UPI"),
        (PAYMENT_CREDIT, "Credit"),
    ]

    bill_number = models.CharField(max_length=40, unique=True)
    checkout_token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    taxable_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0")
    )
    tax_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0")
    )
    pricing_mode_snapshot = models.CharField(
        max_length=10, choices=ShopSettings.PRICING_MODE_CHOICES
    )
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_COMPLETED
    )
    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_CHOICES, blank=True, default=""
    )
    item_count = models.PositiveIntegerField(default=0)

    objects = SaleQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["bill_number"], name="sale_bill_number_idx"),
            models.Index(fields=["created_at"], name="sale_created_idx"),
        ]

    def __str__(self) -> str:
        return self.bill_number

    @property
    def total_quantity(self) -> int:
        return self.item_count


class SaleItem(models.Model):
    """A line item stored as an immutable snapshot for historical accuracy."""

    sale = models.ForeignKey(
        Sale, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sale_items",
    )
    product_name_snapshot = models.CharField(max_length=200)
    barcode_snapshot = models.CharField(max_length=64, blank=True, default="")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    gst_rate_snapshot = models.DecimalField(max_digits=5, decimal_places=2)
    taxable_amount = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1), name="sale_item_quantity_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product_name_snapshot}"


class StockMovement(models.Model):
    """An auditable, signed change to product stock."""

    REASON_OPENING = "opening"
    REASON_SALE = "sale"
    REASON_ADJUSTMENT = "adjustment"
    REASON_RESTORE = "restore"
    REASON_CHOICES = [
        (REASON_OPENING, "Opening stock"),
        (REASON_SALE, "Sale"),
        (REASON_ADJUSTMENT, "Manual adjustment"),
        (REASON_RESTORE, "Restore"),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_movements"
    )
    quantity_change = models.IntegerField(
        help_text="Signed change: negative reduces stock, positive increases it."
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    sale = models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        sign = "+" if self.quantity_change >= 0 else ""
        return f"{self.product} {sign}{self.quantity_change} ({self.reason})"

    @classmethod
    def record(cls, *, product, quantity_change, reason, sale=None, note=""):
        """Create a movement and apply the signed change to product stock."""
        movement = cls.objects.create(
            product=product,
            quantity_change=quantity_change,
            reason=reason,
            sale=sale,
            note=note,
        )
        Product.objects.filter(pk=product.pk).update(
            stock_quantity=F("stock_quantity") + quantity_change
        )
        product.refresh_from_db(fields=["stock_quantity"])
        return movement
