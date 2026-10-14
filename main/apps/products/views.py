"""Product list, create, edit, deactivate, and stock adjustment views."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.billing.models import StockMovement

from .forms import ProductForm, StockAdjustmentForm
from .models import Product


def product_list(request):
    query = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") or "active"

    products = Product.objects.all()
    if query:
        products = products.search(query)
    if status == "active":
        products = products.filter(is_active=True)
    elif status == "inactive":
        products = products.filter(is_active=False)
    elif status == "low":
        from apps.core.models import ShopSettings

        threshold = ShopSettings.get_solo().low_stock_threshold
        products = products.filter(
            is_active=True, stock_quantity__lte=threshold
        )

    paginator = Paginator(products, 20)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "page_title": "Products",
        "page": page,
        "query": query,
        "status": status,
        "total_count": paginator.count,
        "has_products": Product.objects.exists(),
    }
    return render(request, "products/list.html", context)


def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                product = form.save()
                if product.stock_quantity > 0:
                    # The form already saved the quantity; log the movement
                    # without re-applying the change to stock.
                    StockMovement.objects.create(
                        product=product,
                        quantity_change=product.stock_quantity,
                        reason=StockMovement.REASON_OPENING,
                        note="Opening stock",
                    )
            messages.success(request, f"Product '{product.name}' added.")
            return redirect("products:list")
    else:
        form = ProductForm()

    return render(
        request,
        "products/form.html",
        {"form": form, "page_title": "Add product", "is_create": True},
    )


def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        previous_stock = product.stock_quantity
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            with transaction.atomic():
                product = form.save()
                delta = product.stock_quantity - previous_stock
                if delta != 0:
                    # Bypass StockMovement.record's stock update: the form
                    # already saved the new quantity, so only log the movement.
                    StockMovement.objects.create(
                        product=product,
                        quantity_change=delta,
                        reason=StockMovement.REASON_ADJUSTMENT,
                        note="Adjusted while editing product",
                    )
            messages.success(request, f"Product '{product.name}' updated.")
            return redirect("products:list")
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "products/form.html",
        {"form": form, "product": product, "page_title": "Edit product"},
    )


@require_POST
def product_toggle_active(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=["is_active", "updated_at"])
    state = "activated" if product.is_active else "deactivated"
    messages.success(request, f"'{product.name}' {state}.")
    return redirect("products:list")


def product_stock(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data["quantity"]
            action = form.cleaned_data["action"]
            note = form.cleaned_data.get("note") or ""
            delta = quantity if action == "add" else -quantity
            if action == "remove" and quantity > product.stock_quantity:
                messages.error(
                    request,
                    f"Cannot remove {quantity}; only {product.stock_quantity} in stock.",
                )
            else:
                with transaction.atomic():
                    StockMovement.record(
                        product=product,
                        quantity_change=delta,
                        reason=StockMovement.REASON_ADJUSTMENT,
                        note=note or "Manual stock adjustment",
                    )
                messages.success(
                    request,
                    f"Stock for '{product.name}' adjusted by {delta:+d}.",
                )
                return redirect("products:edit", pk=product.pk)
    else:
        form = StockAdjustmentForm()

    movements = product.stock_movements.all()[:25]
    return render(
        request,
        "products/stock.html",
        {
            "product": product,
            "form": form,
            "movements": movements,
            "page_title": f"Stock - {product.name}",
        },
    )
