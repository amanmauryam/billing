"""Redirect to first-run setup until the shop is configured."""

from django.shortcuts import redirect
from django.urls import reverse

from .models import ShopSettings

EXEMPT_PREFIXES = ("/setup", "/static", "/media", "/admin", "/favicon")


class SetupRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not path.startswith(EXEMPT_PREFIXES):
            if not ShopSettings.get_solo().is_configured:
                return redirect(reverse("core:setup"))
        return self.get_response(request)
