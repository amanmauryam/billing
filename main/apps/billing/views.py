"""POS, checkout, and sales history views."""

import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from apps.products.models import Product

from . import services
from .models import Sale


def _product_payload(product):
    return {
        "id": product.pk,
        "name": product.name,
        "barcode": product.barcode or "",
        "price": str(product.selling_price),
        "gst_rate": str(product.gst_rate),
        "stock": product.stock_quantity,
        "is_active": product.is_active,
        "stock_status": product.stock_status,
    }


@ensure_csrf_cookie
def pos_view(request):
    from apps.core.models import ShopSettings

    shop = ShopSettings.get_solo()
    return render(
        request,
        "pos/pos.html",
        {
            "page_title": "New Bill",
            "pricing_mode": shop.pricing_mode,
            "pricing_inclusive": shop.pricing_mode == ShopSettings.PRICING_INCLUSIVE,
        },
    )


@require_GET
def product_search(request):
    query = (request.GET.get("q") or "").strip()
    if not query:
        return JsonResponse({"results": []})

    exact = Product.objects.active().filter(barcode__iexact=query).first()
    results = list(Product.objects.active().search(query)[:20])
    if exact is not None and all(p.pk != exact.pk for p in results):
        results.insert(0, exact)

    return JsonResponse(
        {
            "results": [_product_payload(p) for p in results],
            "exact_id": exact.pk if exact is not None else None,
        }
    )


@require_GET
def barcode_lookup(request):
    barcode = (request.GET.get("barcode") or "").strip()
    if not barcode:
        return JsonResponse({"found": False, "error": "Empty barcode."}, status=400)
    product = Product.objects.filter(barcode__iexact=barcode).first()
    if product is None:
        return JsonResponse({"found": False, "barcode": barcode})
    if not product.is_active:
        return JsonResponse(
            {
                "found": False,
                "error": f"'{product.name}' is inactive and cannot be sold.",
                "barcode": barcode,
            }
        )
    return JsonResponse({"found": True, "product": _product_payload(product)})


@require_POST
def checkout(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"ok": False, "error": "Malformed request."}, status=400
        )

    token = payload.get("token")
    items = payload.get("items")
    payment_method = payload.get("payment_method") or ""

    try:
        sale, created = services.perform_checkout(
            cart_payload=items,
            checkout_token=token,
            payment_method=payment_method,
        )
    except services.CheckoutError as exc:
        return JsonResponse({"ok": False, "error": exc.message}, status=400)

    return JsonResponse(
        {
            "ok": True,
            "created": created,
            "bill_number": sale.bill_number,
            "grand_total": str(sale.grand_total),
            "receipt_url": reverse("billing:sale_detail", args=[sale.bill_number]),
            "new_bill_url": reverse("billing:pos"),
        }
    )


def sale_list(request):
    bill_number = (request.GET.get("bill") or "").strip()
    date_str = (request.GET.get("date") or "").strip()
    payment = (request.GET.get("payment") or "").strip()

    sales = Sale.objects.completed()
    if bill_number:
        sales = sales.filter(bill_number__icontains=bill_number)
    if payment:
        if payment in dict(Sale.PAYMENT_CHOICES):
            sales = sales.filter(payment_method=payment)
        else:
            messages.warning(request, "Ignoring an unknown payment filter.")
            payment = ""
    if date_str:
        try:
            from datetime import datetime, time

            day = datetime.strptime(date_str, "%Y-%m-%d").date()
            start = timezone.make_aware(datetime.combine(day, time.min))
            end = timezone.make_aware(datetime.combine(day, time.max))
            sales = sales.filter(created_at__range=(start, end))
        except ValueError:
            messages.warning(request, "Ignoring an invalid date filter.")

    paginator = Paginator(sales, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "sales/list.html",
        {
            "page_title": "Sales",
            "page": page,
            "bill_number": bill_number,
            "date_str": date_str,
            "payment": payment,
            "payment_choices": Sale.PAYMENT_CHOICES,
            "total_count": paginator.count,
            "has_sales": Sale.objects.completed().exists(),
            "has_filters": bool(bill_number or date_str or payment),
        },
    )


def sale_detail(request, bill_number):
    sale = get_object_or_404(
        Sale.objects.prefetch_related("items"), bill_number=bill_number
    )
    return render(
        request,
        "sales/detail.html",
        {
            "page_title": f"Bill {sale.bill_number}",
            "sale": sale,
            "items": sale.items.all(),
            "print_mode": request.GET.get("print") == "1",
        },
    )
