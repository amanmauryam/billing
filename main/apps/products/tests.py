from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.billing.models import StockMovement
from apps.core.models import ShopSettings

from .forms import ProductForm
from .models import Product, normalize_barcode


class NormalizeBarcodeTests(TestCase):
    def test_blank_values_become_none(self):
        self.assertIsNone(normalize_barcode("   "))
        self.assertIsNone(normalize_barcode(""))
        self.assertIsNone(normalize_barcode(None))

    def test_whitespace_is_trimmed(self):
        self.assertEqual(normalize_barcode("  12345  "), "12345")


class ProductModelTests(TestCase):
    def test_multiple_products_without_barcode(self):
        Product.objects.create(name="A", selling_price="10", gst_rate="5", stock_quantity=1)
        Product.objects.create(name="B", selling_price="10", gst_rate="5", stock_quantity=1)
        self.assertEqual(Product.objects.count(), 2)
        self.assertTrue(all(p.barcode is None for p in Product.objects.all()))

    def test_stock_status(self):
        out = Product.objects.create(name="Out", selling_price="1", gst_rate="0", stock_quantity=0)
        low = Product.objects.create(name="Low", selling_price="1", gst_rate="0", stock_quantity=3)
        ok = Product.objects.create(name="Ok", selling_price="1", gst_rate="0", stock_quantity=50)
        self.assertEqual(out.stock_status, "out")
        self.assertEqual(low.stock_status, "low")
        self.assertEqual(ok.stock_status, "ok")

    def test_search_matches_name_and_barcode(self):
        Product.objects.create(name="Parle-G", barcode="8901", selling_price="10", gst_rate="5", stock_quantity=5)
        Product.objects.create(name="Soap", barcode="7777", selling_price="30", gst_rate="18", stock_quantity=5)
        self.assertEqual(Product.objects.search("parle").count(), 1)
        self.assertEqual(Product.objects.search("7777").count(), 1)


class ProductFormTests(TestCase):
    def _data(self, **overrides):
        data = {
            "name": "Biscuits",
            "barcode": "",
            "selling_price": "20.00",
            "gst_rate": "18",
            "stock_quantity": "10",
            "is_active": "on",
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = ProductForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_name_rejected(self):
        form = ProductForm(data=self._data(name="   "))
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_negative_price_rejected(self):
        form = ProductForm(data=self._data(selling_price="-1"))
        self.assertFalse(form.is_valid())
        self.assertIn("selling_price", form.errors)

    def test_negative_stock_rejected(self):
        form = ProductForm(data=self._data(stock_quantity="-3"))
        self.assertFalse(form.is_valid())
        self.assertIn("stock_quantity", form.errors)

    def test_invalid_gst_rejected(self):
        form = ProductForm(data=self._data(gst_rate="150"))
        self.assertFalse(form.is_valid())
        self.assertIn("gst_rate", form.errors)

    def test_duplicate_barcode_rejected(self):
        Product.objects.create(
            name="Existing", barcode="123456", selling_price="5", gst_rate="0", stock_quantity=1
        )
        form = ProductForm(data=self._data(barcode="123456"))
        self.assertFalse(form.is_valid())
        self.assertIn("barcode", form.errors)

    def test_duplicate_barcode_allowed_for_same_instance(self):
        product = Product.objects.create(
            name="Existing", barcode="123456", selling_price="5", gst_rate="0", stock_quantity=1
        )
        form = ProductForm(
            data=self._data(name="Renamed", barcode="123456"), instance=product
        )
        self.assertTrue(form.is_valid(), form.errors)


class ProductViewTests(TestCase):
    def setUp(self):
        shop = ShopSettings.get_solo()
        shop.is_configured = True
        shop.save()
        self.product = Product.objects.create(
            name="Tea", barcode="100", selling_price="250.00", gst_rate="5", stock_quantity=20
        )

    def test_list_renders(self):
        response = self.client.get(reverse("products:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tea")

    def test_create_records_opening_stock_movement(self):
        response = self.client.post(
            reverse("products:create"),
            {
                "name": "Coffee",
                "barcode": "",
                "selling_price": "300",
                "gst_rate": "18",
                "stock_quantity": "7",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("products:list"))
        coffee = Product.objects.get(name="Coffee")
        self.assertEqual(coffee.stock_quantity, 7)
        self.assertEqual(
            StockMovement.objects.filter(
                product=coffee, reason=StockMovement.REASON_OPENING
            ).count(),
            1,
        )

    def test_edit_adjustment_records_movement(self):
        self.client.post(
            reverse("products:edit", args=[self.product.pk]),
            {
                "name": "Tea",
                "barcode": "100",
                "selling_price": "250.00",
                "gst_rate": "5",
                "stock_quantity": "12",
                "is_active": "on",
            },
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 12)
        movement = StockMovement.objects.filter(
            product=self.product, reason=StockMovement.REASON_ADJUSTMENT
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity_change, -8)

    def test_deactivate_toggle(self):
        self.client.post(reverse("products:toggle", args=[self.product.pk]))
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
