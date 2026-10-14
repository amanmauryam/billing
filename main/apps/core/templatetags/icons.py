"""Inline, locally bundled Lucide icons.

Icons are read from ``static/icons`` (populated from the ``lucide-static``
package so the app stays fully offline) and inlined as SVG so they inherit
``currentColor`` and can be sized with Tailwind utilities.
"""

import re
from functools import lru_cache
from pathlib import Path

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

ICON_DIR = Path(settings.BASE_DIR) / "static" / "icons"

_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_ROOT_TAG_RE = re.compile(r"<svg\b[^>]*>", re.S)
_CLASS_RE = re.compile(r'\sclass="[^"]*"')
_SIZE_RE = re.compile(r'\s(?:width|height)="[^"]*"')


@lru_cache(maxsize=None)
def _load(name: str) -> str:
    path = ICON_DIR / f"{name}.svg"
    if not path.exists():
        return ""
    svg = path.read_text(encoding="utf-8")
    svg = _COMMENT_RE.sub("", svg)
    # Only strip sizing/class from the root <svg> tag so child shapes that use
    # width/height (e.g. <rect>) keep their dimensions.
    match = _ROOT_TAG_RE.search(svg)
    if not match:
        return ""
    root = match.group(0)
    root = _CLASS_RE.sub("", root)
    root = _SIZE_RE.sub("", root)
    svg = svg[: match.start()] + root + svg[match.end() :]
    return svg.strip()


@register.simple_tag
def icon(name: str, classes: str = "h-5 w-5") -> str:
    svg = _load(name)
    if not svg:
        return ""
    return mark_safe(
        svg.replace(
            "<svg",
            f'<svg class="{classes}" aria-hidden="true" focusable="false"',
            1,
        )
    )
