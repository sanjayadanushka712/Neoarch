"""Package screenshots from Flathub AppStream metadata.

Flathub exposes the AppStream record of every app (including the ones
already installed) as JSON. This module keeps the network access and the
size selection out of the UI so the carousel can stay a dumb renderer.
"""

import json
import urllib.parse
import urllib.request
from typing import Dict, List

__all__ = ["flathub_screenshots", "clear_cache"]

FLATHUB_APPSTREAM = "https://flathub.org/api/v2/appstream/{app_id}"
_MAX_WIDTH = 900

_cache: Dict[str, List[Dict[str, str]]] = {}


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _pick_size(sizes: List[Dict]) -> str:
    """Pick the largest image that fits the detail card, else the smallest."""
    candidates = [s for s in sizes if isinstance(s, dict) and s.get("src")]
    if not candidates:
        return ""
    fitting = [s for s in candidates if _int(s.get("width")) <= _MAX_WIDTH]
    if fitting:
        return max(fitting, key=lambda s: _int(s.get("width")))["src"]
    return min(candidates, key=lambda s: _int(s.get("width")))["src"]


def flathub_screenshots(app_id: str, timeout: int = 8,
                        refresh: bool = False) -> List[Dict[str, str]]:
    """Return ``[{"caption", "url"}]`` for a Flathub app, newest first."""
    key = (app_id or "").strip()
    if not key:
        return []
    if not refresh and key in _cache:
        return [dict(slide) for slide in _cache[key]]

    slides: List[Dict[str, str]] = []
    try:
        url = FLATHUB_APPSTREAM.format(app_id=urllib.parse.quote(key))
        request = urllib.request.Request(
            url, headers={"User-Agent": "NeoArch"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        for shot in data.get("screenshots") or []:
            if not isinstance(shot, dict):
                continue
            image = _pick_size(shot.get("sizes") or [])
            if image:
                slides.append({
                    "caption": shot.get("caption") or "",
                    "url": image,
                })
    except Exception:
        slides = []
    _cache[key] = slides
    return [dict(slide) for slide in slides]


def clear_cache():
    _cache.clear()
