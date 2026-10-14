"""Template helpers for consistent money display."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

SYMBOL = "\u20b9"


@register.filter
def rupees(value) -> str:
    """Render a Decimal as ``₹1,234.50`` using Indian grouping."""
    if value in (None, ""):
        return f"{SYMBOL}0.00"
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return f"{SYMBOL}{value}"

    negative = amount < 0
    quantized = abs(amount).quantize(Decimal("0.01"))
    whole, _, fraction = f"{quantized:f}".partition(".")
    whole = whole or "0"

    # Indian grouping: last 3 digits, then groups of 2.
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups) + "," + tail

    formatted = f"{whole}.{fraction[:2].ljust(2, '0')}"
    if negative:
        formatted = "-" + formatted
    return f"{SYMBOL}{formatted}"
