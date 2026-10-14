"""Forms for shop-wide settings."""

from django import forms

from .models import ShopSettings


class StyledFormMixin:
    """Applies the shared input styling to text-like widgets."""

    def _apply_styles(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                continue
            base = "input h-auto py-2 min-h-11" if isinstance(
                widget, forms.Textarea
            ) else "input"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{base} {existing}".strip()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_styles()


class ShopSettingsForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ShopSettings
        fields = [
            "shop_name",
            "address",
            "phone",
            "gstin",
            "state",
            "receipt_width",
            "pricing_mode",
            "low_stock_threshold",
            "receipt_footer",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "receipt_footer": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_shop_name(self):
        name = (self.cleaned_data.get("shop_name") or "").strip()
        if not name:
            raise forms.ValidationError("Shop name is required.")
        return name


class SetupForm(ShopSettingsForm):
    """First-run setup form (same fields, framed as setup)."""

    class Meta(ShopSettingsForm.Meta):
        pass
