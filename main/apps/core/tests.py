import sqlite3
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from apps.billing import services as billing_services
from apps.billing.models import Sale
from apps.products.models import Product

from . import services
from .models import ShopSettings


def configure_shop(**overrides):
    shop = ShopSettings.get_solo()
    shop.shop_name = "Test Shop"
    shop.is_configured = True
    for key, value in overrides.items():
        setattr(shop, key, value)
    shop.save()
    return shop


class ShopSettingsModelTests(TestCase):
    def test_single_row_enforced(self):
        a = ShopSettings.get_solo()
        a.shop_name = "One"
        a.save()
        b = ShopSettings.get_solo()
        b.shop_name = "Two"
        b.save()
        self.assertEqual(ShopSettings.objects.count(), 1)
        self.assertEqual(ShopSettings.get_solo().shop_name, "Two")


class SetupMiddlewareTests(TestCase):
    def test_redirects_to_setup_when_not_configured(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(response, reverse("core:setup"))

    def test_setup_page_renders_when_not_configured(self):
        response = self.client.get(reverse("core:setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Set up your shop")
        self.assertContains(response, "Finish setup")

    def test_setup_marks_shop_configured(self):
        response = self.client.post(
            reverse("core:setup"),
            {
                "shop_name": "Fresh Mart",
                "address": "",
                "phone": "",
                "gstin": "",
                "state": "",
                "receipt_width": "58",
                "pricing_mode": "inclusive",
                "low_stock_threshold": "5",
                "receipt_footer": "Thanks",
            },
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertTrue(ShopSettings.get_solo().is_configured)

    def test_configured_shop_can_reach_dashboard(self):
        configure_shop()
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)


class DashboardTests(TestCase):
    def setUp(self):
        configure_shop(low_stock_threshold=5)
        self.product = Product.objects.create(
            name="Rice", selling_price="100", gst_rate="5", stock_quantity=50
        )
        Product.objects.create(
            name="Salt", selling_price="20", gst_rate="5", stock_quantity=2
        )

    def test_dashboard_totals_from_saved_sales(self):
        billing_services.perform_checkout(
            cart_payload=[{"product_id": self.product.pk, "quantity": 2}],
            checkout_token="dash-token",
        )
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["today_count"], 1)
        self.assertEqual(response.context["today_total"], Decimal("200.00"))
        self.assertEqual(response.context["low_stock_count"], 1)


class SettingsViewTests(TestCase):
    def test_update_pricing_mode(self):
        configure_shop(pricing_mode=ShopSettings.PRICING_INCLUSIVE)
        response = self.client.post(
            reverse("core:settings"),
            {
                "shop_name": "Test Shop",
                "address": "",
                "phone": "",
                "gstin": "",
                "state": "",
                "receipt_width": "80",
                "pricing_mode": ShopSettings.PRICING_EXCLUSIVE,
                "low_stock_threshold": "10",
                "receipt_footer": "Bye",
            },
        )
        self.assertRedirects(response, reverse("core:settings"))
        shop = ShopSettings.get_solo()
        self.assertEqual(shop.pricing_mode, ShopSettings.PRICING_EXCLUSIVE)
        self.assertEqual(shop.receipt_width, "80")

    def test_blank_shop_name_rejected(self):
        configure_shop()
        response = self.client.post(
            reverse("core:settings"),
            {
                "shop_name": "   ",
                "receipt_width": "58",
                "pricing_mode": "inclusive",
                "low_stock_threshold": "5",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "required")


class BackupServiceTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)
        self.db_path = self.tmp_path / "source.sqlite3"
        self.backup_dir = self.tmp_path / "backups"
        self.backup_dir.mkdir()

        conn = sqlite3.connect(str(self.db_path))
        conn.execute("CREATE TABLE billing_sale (id integer primary key, total text)")
        conn.execute("INSERT INTO billing_sale (total) VALUES ('100.00')")
        conn.commit()
        conn.close()

        self.patches = [
            mock.patch.object(services, "get_backup_dir", return_value=self.backup_dir),
            mock.patch.object(services, "get_database_path", return_value=self.db_path),
        ]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_create_backup_writes_file(self):
        path = services.create_backup(label="manual")
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 0)

    def test_list_backups(self):
        services.create_backup(label="one")
        items = services.list_backups()
        self.assertEqual(len(items), 1)
        self.assertIn("one", items[0]["name"])

    def test_restore_replaces_database_and_makes_safety_backup(self):
        backup = services.create_backup(label="good")

        # Mutate the "current" database after the backup was taken.
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE billing_sale SET total = '999.00'")
        conn.commit()
        conn.close()

        safety = services.restore_backup(backup)
        self.assertTrue(Path(safety).exists())

        conn = sqlite3.connect(str(self.db_path))
        total = conn.execute("SELECT total FROM billing_sale").fetchone()[0]
        conn.close()
        self.assertEqual(total, "100.00")

    def test_restore_rejects_non_pos_file(self):
        bad = self.tmp_path / "bad.sqlite3"
        conn = sqlite3.connect(str(bad))
        conn.execute("CREATE TABLE unrelated (id integer)")
        conn.commit()
        conn.close()
        with self.assertRaises(services.BackupError):
            services.restore_backup(bad)


class BackupViewTests(TestCase):
    def test_backup_page_renders(self):
        configure_shop()
        with mock.patch.object(services, "list_backups", return_value=[]):
            response = self.client.get(reverse("core:backup"))
        self.assertEqual(response.status_code, 200)

    def test_restore_requires_confirmation(self):
        configure_shop()
        response = self.client.post(
            reverse("core:backup_restore"), {"backup_name": "missing.sqlite3"}
        )
        self.assertRedirects(response, reverse("core:backup"))


class SaleIntegrityTests(TestCase):
    def test_dashboard_ignores_no_sales(self):
        configure_shop()
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.context["today_count"], 0)
        self.assertEqual(Sale.objects.count(), 0)
