"""Product forms with server-side validation."""

from decimal import Decimal

from django import forms

from apps.core.forms import StyledFormMixin

from .models import Product, normalize_barcode


class ProductForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "barcode",
            "selling_price",
            "gst_rate",
            "stock_quantity",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
            "barcode": forms.TextInput(attrs={"autocomplete": "off"}),
            "selling_price": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "inputmode": "decimal"}
            ),
            "gst_rate": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "max": "100", "inputmode": "decimal"}
            ),
            "stock_quantity": forms.NumberInput(
                attrs={"step": "1", "min": "0", "inputmode": "numeric"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "peer sr-only"}),
        }
        labels = {
            "stock_quantity": "Stock quantity",
            "gst_rate": "GST rate (%)",
            "selling_price": "Selling price",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].initial = True
        self.fields["is_active"].required = False
        self.fields["gst_rate"].initial = (
            self.instance.gst_rate if self.instance.pk else Decimal("0")
        )
        if self.instance.pk is None:
            self.fields["stock_quantity"].label = "Opening stock quantity"

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Product name is required.")
        return name

    def clean_barcode(self):
        barcode = normalize_barcode(self.cleaned_data.get("barcode"))
        if barcode is None:
            return None
        qs = Product.objects.filter(barcode__iexact=barcode)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Another product already uses this barcode."
            )
        return barcode

    def clean_selling_price(self):
        price = self.cleaned_data.get("selling_price")
        if price is None:
            raise forms.ValidationError("Selling price is required.")
        if price < 0:
            raise forms.ValidationError("Selling price cannot be negative.")
        return price

    def clean_gst_rate(self):
        rate = self.cleaned_data.get("gst_rate")
        if rate is None:
            raise forms.ValidationError("GST rate is required.")
        if rate < 0 or rate > 100:
            raise forms.ValidationError("GST rate must be between 0 and 100.")
        return rate

    def clean_stock_quantity(self):
        quantity = self.cleaned_data.get("stock_quantity")
        if quantity is None:
            raise forms.ValidationError("Stock quantity is required.")
        if quantity < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return quantity


class StockAdjustmentForm(StyledFormMixin, forms.Form):
    """Manual stock adjustment that records an auditable movement."""

    REASON_CHOICES = [
        ("add", "Add stock"),
        ("remove", "Remove stock"),
    ]

    action = forms.ChoiceField(choices=REASON_CHOICES, initial="add")
    quantity = forms.IntegerField(min_value=1)
    note = forms.CharField(max_length=255, required=False)
