"""Dashboard, settings, first-run setup, and backup/restore views."""

from datetime import datetime, time

from django.contrib import messages
from django.db import connections
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.billing.models import Sale
from apps.products.models import Product

from . import services
from .forms import SetupForm, ShopSettingsForm
from .models import ShopSettings


def _local_day_bounds(day=None):
    day = day or timezone.localdate()
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = timezone.make_aware(datetime.combine(day, time.max))
    return start, end


def dashboard(request):
    settings_row = ShopSettings.get_solo()
    start, end = _local_day_bounds()

    today_sales = Sale.objects.completed().filter(
        created_at__range=(start, end)
    )
    today_total = today_sales.aggregate(total=Sum("grand_total"))["total"] or 0
    today_count = today_sales.count()

    active_products = Product.objects.active()
    threshold = settings_row.low_stock_threshold
    low_stock_products = (
        active_products.filter(stock_quantity__gt=0, stock_quantity__lte=threshold)
        .order_by("stock_quantity", "name")[:10]
    )
    out_of_stock_count = active_products.filter(stock_quantity__lte=0).count()
    low_stock_count = active_products.filter(
        stock_quantity__gt=0, stock_quantity__lte=threshold
    ).count()

    recent_sales = Sale.objects.completed()[:8]

    context = {
        "page_title": "Dashboard",
        "today_total": today_total,
        "today_count": today_count,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "low_stock_products": low_stock_products,
        "recent_sales": recent_sales,
        "product_count": active_products.count(),
        "has_products": active_products.exists(),
        "has_sales": Sale.objects.completed().exists(),
    }
    return render(request, "core/dashboard.html", context)


def setup(request):
    settings_row = ShopSettings.get_solo()
    if settings_row.is_configured and not request.GET.get("edit"):
        return redirect("core:dashboard")

    if request.method == "POST":
        form = SetupForm(request.POST, instance=settings_row)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.is_configured = True
            obj.save()
            messages.success(
                request, "Shop setup complete. You can start billing now."
            )
            return redirect("core:dashboard")
    else:
        form = SetupForm(instance=settings_row)

    return render(
        request,
        "core/setup.html",
        {"form": form, "page_title": "Shop setup", "is_setup": True},
    )


def settings_view(request):
    settings_row = ShopSettings.get_solo()
    if request.method == "POST":
        form = ShopSettingsForm(request.POST, instance=settings_row)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.is_configured = True
            obj.save()
            messages.success(request, "Settings saved.")
            return redirect("core:settings")
    else:
        form = ShopSettingsForm(instance=settings_row)

    return render(
        request,
        "core/settings.html",
        {"form": form, "page_title": "Settings", "settings": settings_row},
    )


def backup_view(request):
    backups = services.list_backups()
    return render(
        request,
        "core/backup.html",
        {
            "page_title": "Backup & Restore",
            "backups": backups,
            "backup_dir": services.get_backup_dir(),
            "database_path": services.get_database_path(),
        },
    )


@require_POST
def backup_create(request):
    try:
        path = services.create_backup(label="manual")
    except services.BackupError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Backup created: {path.name}")
    return redirect("core:backup")


@require_POST
def backup_restore(request):
    backup_name = (request.POST.get("backup_name") or "").strip()
    if not backup_name:
        messages.error(request, "Select a backup to restore.")
        return redirect("core:backup")

    backup_dir = services.get_backup_dir().resolve()
    candidate = (backup_dir / backup_name).resolve()
    if backup_dir not in candidate.parents or not candidate.exists():
        messages.error(request, "That backup file could not be found.")
        return redirect("core:backup")

    if request.POST.get("confirm") != "yes":
        messages.error(request, "Restore cancelled: confirmation was not provided.")
        return redirect("core:backup")

    try:
        safety = services.restore_backup(candidate)
    except services.BackupError as exc:
        messages.error(request, str(exc))
    else:
        # Drop cached connections so the restored file is used immediately.
        connections.close_all()
        messages.success(
            request,
            f"Database restored from {backup_name}. "
            f"A safety backup was saved as {safety.name}.",
        )
    return redirect("core:backup")
