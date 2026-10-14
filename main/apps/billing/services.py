"""Money, GST, and checkout services.

All monetary maths use :class:`decimal.Decimal` from validated values. Amounts
are quantized to two decimal places using ``ROUND_HALF_UP`` at the *line*
level, and invoice totals are the sum of those already-rounded line values.
This keeps the printed lines and the printed totals reconciled exactly.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import IntegrityError, transaction

from apps.core.models import ShopSettings
from apps.products.models import Product

from .models import Sale, SaleItem, StockMovement

MONEY_QUANTUM = Decimal("0.01")
HUNDRED = Decimal("100")

# Upper bounds protect against accidental or malicious oversized payloads.
MAX_LINE_QUANTITY = 100_000
MAX_CART_LINES = 500


class CheckoutError(Exception):
    """A recoverable, user-facing checkout failure."""

    def __init__(self, message, *, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CheckoutError("Invalid numeric value received.") from exc


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineCalculation:
    quantity: int
    unit_price: Decimal
    gst_rate: Decimal
    raw_total: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    line_total: Decimal


def calculate_line(quantity, unit_price, gst_rate, pricing_mode) -> LineCalculation:
    """Calculate a single line's amounts for the given pricing mode."""
    quantity = int(quantity)
    unit_price = quantize_money(to_decimal(unit_price))
    gst_rate = to_decimal(gst_rate)
    raw_total = unit_price * quantity

    if pricing_mode == ShopSettings.PRICING_INCLUSIVE:
        line_total = quantize_money(raw_total)
        if gst_rate == 0:
            taxable_amount = line_total
        else:
            divisor = Decimal("1") + (gst_rate / HUNDRED)
            taxable_amount = quantize_money(raw_total / divisor)
        tax_amount = line_total - taxable_amount
    else:
        taxable_amount = quantize_money(raw_total)
        tax_amount = quantize_money(taxable_amount * gst_rate / HUNDRED)
        line_total = taxable_amount + tax_amount

    return LineCalculation(
        quantity=quantity,
        unit_price=unit_price,
        gst_rate=gst_rate,
        raw_total=quantize_money(raw_total),
        taxable_amount=taxable_amount,
        tax_amount=tax_amount,
        line_total=quantize_money(line_total),
    )


@dataclass
class CalculatedCart:
    lines: list[dict]
    subtotal: Decimal
    taxable_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    item_count: int


def calculate_cart(raw_lines, pricing_mode) -> CalculatedCart:
    """Validate and price raw cart lines ``[{product, quantity}, ...]``."""
    priced = []
    subtotal = Decimal("0.00")
    taxable_total = Decimal("0.00")
    tax_total = Decimal("0.00")
    grand_total = Decimal("0.00")
    item_count = 0

    for raw in raw_lines:
        product = raw["product"]
        try:
            quantity = int(raw["quantity"])
        except (TypeError, ValueError) as exc:
            raise CheckoutError(
                f"Invalid quantity for {product.name}."
            ) from exc
        if quantity < 1:
            raise CheckoutError(f"Quantity for {product.name} must be at least 1.")
        if quantity > MAX_LINE_QUANTITY:
            raise CheckoutError(f"Quantity for {product.name} is too large.")

        calc = calculate_line(
            quantity, product.selling_price, product.gst_rate, pricing_mode
        )
        priced.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": calc.unit_price,
                "gst_rate": calc.gst_rate,
                "taxable_amount": calc.taxable_amount,
                "tax_amount": calc.tax_amount,
                "line_total": calc.line_total,
            }
        )
        subtotal += calc.raw_total
        taxable_total += calc.taxable_amount
        tax_total += calc.tax_amount
        grand_total += calc.line_total
        item_count += quantity

    return CalculatedCart(
        lines=priced,
        subtotal=quantize_money(subtotal),
        taxable_total=quantize_money(taxable_total),
        tax_total=quantize_money(tax_total),
        grand_total=quantize_money(grand_total),
        item_count=item_count,
    )


def generate_bill_number() -> str:
    """Return the next human-readable bill number, e.g. ``INV-20261014-0007``."""
    from django.utils import timezone

    today = timezone.localtime()
    prefix = f"INV-{today:%Y%m%d}-"
    count = Sale.objects.filter(bill_number__startswith=prefix).count()
    return f"{prefix}{count + 1:04d}"


def normalize_cart_payload(payload) -> list[dict]:
    """Validate the shape of a submitted cart and collapse duplicate lines."""
    if not isinstance(payload, list):
        raise CheckoutError("Invalid cart data.")
    if not payload:
        raise CheckoutError("The cart is empty.")
    if len(payload) > MAX_CART_LINES:
        raise CheckoutError("Too many distinct items in one bill.")

    merged: dict[int, int] = {}
    for entry in payload:
        if not isinstance(entry, dict):
            raise CheckoutError("Invalid cart item.")
        try:
            product_id = int(entry.get("product_id"))
            quantity = int(entry.get("quantity"))
        except (TypeError, ValueError) as exc:
            raise CheckoutError("Invalid cart item.") from exc
        if quantity < 1:
            raise CheckoutError("Item quantities must be at least 1.")
        merged[product_id] = merged.get(product_id, 0) + quantity

    for product_id, quantity in merged.items():
        if quantity > MAX_LINE_QUANTITY:
            raise CheckoutError("Item quantity is too large.")

    return [
        {"product_id": pid, "quantity": qty} for pid, qty in merged.items()
    ]


def perform_checkout(*, cart_payload, checkout_token, payment_method=""):
    """Create a sale atomically, deduct stock once, and return ``(sale, created)``.

    ``created`` is ``False`` when an identical checkout token has already been
    processed, in which case the original sale is returned unchanged.
    """
    if not checkout_token or not str(checkout_token).strip():
        raise CheckoutError("Missing checkout request token.")
    checkout_token = str(checkout_token).strip()

    # Fast path: an earlier identical request already produced a sale.
    existing = Sale.objects.filter(checkout_token=checkout_token).first()
    if existing is not None:
        return existing, False

    normalized = normalize_cart_payload(cart_payload)
    settings_row = ShopSettings.get_solo()
    pricing_mode = settings_row.pricing_mode

    if payment_method and payment_method not in dict(Sale.PAYMENT_CHOICES):
        raise CheckoutError("Invalid payment method.")

    product_ids = [line["product_id"] for line in normalized]

    try:
        with transaction.atomic():
            # Re-check inside the transaction to close the race window.
            existing = Sale.objects.filter(checkout_token=checkout_token).first()
            if existing is not None:
                return existing, False

            products = {
                product.pk: product
                for product in Product.objects.select_for_update().filter(
                    pk__in=product_ids
                )
            }

            missing = [pid for pid in product_ids if pid not in products]
            if missing:
                raise CheckoutError("One or more products no longer exist.")

            raw_lines = []
            for line in normalized:
                product = products[line["product_id"]]
                if not product.is_active:
                    raise CheckoutError(
                        f"'{product.name}' is no longer available for sale."
                    )
                if line["quantity"] > product.stock_quantity:
                    raise CheckoutError(
                        f"Only {product.stock_quantity} left in stock for "
                        f"'{product.name}'."
                    )
                raw_lines.append(
                    {"product": product, "quantity": line["quantity"]}
                )

            cart = calculate_cart(raw_lines, pricing_mode)

            sale = Sale.objects.create(
                bill_number=generate_bill_number(),
                checkout_token=checkout_token,
                subtotal=cart.subtotal,
                taxable_total=cart.taxable_total,
                tax_total=cart.tax_total,
                grand_total=cart.grand_total,
                pricing_mode_snapshot=pricing_mode,
                payment_method=payment_method or "",
                item_count=cart.item_count,
            )

            sale_items = []
            for line in cart.lines:
                product = line["product"]
                sale_items.append(
                    SaleItem(
                        sale=sale,
                        product=product,
                        product_name_snapshot=product.name,
                        barcode_snapshot=product.barcode or "",
                        quantity=line["quantity"],
                        unit_price=line["unit_price"],
                        gst_rate_snapshot=line["gst_rate"],
                        taxable_amount=line["taxable_amount"],
                        tax_amount=line["tax_amount"],
                        line_total=line["line_total"],
                    )
                )
                # Deduct stock with an auditable movement, exactly once.
                StockMovement.record(
                    product=product,
                    quantity_change=-line["quantity"],
                    reason=StockMovement.REASON_SALE,
                    sale=sale,
                )
            SaleItem.objects.bulk_create(sale_items)

    except IntegrityError:
        # The unique checkout token lost a concurrent race; return the winner.
        existing = Sale.objects.filter(checkout_token=checkout_token).first()
        if existing is not None:
            return existing, False
        raise CheckoutError("The sale could not be completed. Please retry.")

    return sale, True
