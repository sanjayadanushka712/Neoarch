"""Central icon registry for NeoArch.

Every icon lookup goes through this module so assets can be renamed, replaced,
or redirected from a single place.  Callers can use logical names
(``"discover"``), relative paths (``"ui/search.svg"``), or a source name via
:func:`source_icon_path`.
"""

from __future__ import annotations

import os
from functools import lru_cache

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from neoarch.resources.paths import ICONS_DIR

__all__ = [
    "ICON_PATHS",
    "SOURCE_ICONS",
    "BRAND_ICON_CANDIDATES",
    "icon_path",
    "source_icon_path",
    "status_icon_path",
    "brand_icon_path",
    "brand_icon_candidates",
    "brand_logo_path",
    "set_brand_assets",
    "set_brand_pro",
    "has_icon",
    "render_pixmap",
    "render_icon",
]

ICON_PATHS = {
    "about": "about.svg",
    "about_fail": "about-fail.svg",
    "app": "app.png",
    "appimage": "appimage.svg",
    "discover": "discover.svg",
    "docker": "docker.svg",
    "git": "git.svg",
    "groups": "groups.svg",
    "history": "history.svg",
    "installed": "installed.svg",
    "local_builds": "local-builds.svg",
    "local-builds": "local-builds.svg",
    "plugins": "plugins.svg",
    "settings": "settings.svg",
    "updates": "updates.svg",
    "user": "user.svg",
    "app/icon": "app/icon.png",
    "app/icon-pro": "app/icon-pro.png",
    "app/icon-pro-aero": "app/icon-pro-aero.png",
    "app/icon-pro-crystal": "app/icon-pro-crystal.png",
    "app/icon-pro-ember": "app/icon-pro-ember.png",
    "app/icon-pro-endeavour": "app/icon-pro-endeavour.png",
    "app/icon-pro-evergreen": "app/icon-pro-evergreen.png",
    "app/icon-pro-glacier": "app/icon-pro-glacier.png",
    "app/icon-pro-lagoon": "app/icon-pro-lagoon.png",
    "app/icon-pro-moss": "app/icon-pro-moss.png",
    "app/icon-pro-sakura": "app/icon-pro-sakura.png",
    "app/icon-pro-v4": "app/icon-pro-v4.png",
    "app/logo": "app/logo.png",
    "app/logo-pro": "app/logo-pro.png",
    "app/logo-pro-aero": "app/logo-pro-aero.png",
    "app/logo-pro-crystal": "app/logo-pro-crystal.png",
    "app/logo-pro-ember": "app/logo-pro-ember.png",
    "app/logo-pro-endeavour": "app/logo-pro-endeavour.png",
    "app/logo-pro-evergreen": "app/logo-pro-evergreen.png",
    "app/logo-pro-glacier": "app/logo-pro-glacier.png",
    "app/logo-pro-lagoon": "app/logo-pro-lagoon.png",
    "app/logo-pro-moss": "app/logo-pro-moss.png",
    "app/logo-pro-sakura": "app/logo-pro-sakura.png",
    "app/logo-pro-v4": "app/logo-pro-v4.png",
    "app/developer": "app/developer.png",
    "app/qr-code": "app/qr-code.png",
    "app/sponsor-ferreol": "app/sponsor-ferreol.png",
    "sources/aur": "sources/aur.svg",
    "sources/firmware": "sources/firmware.svg",
    "sources/flatpak": "sources/flatpack.svg",
    "sources/git": "sources/git.svg",
    "sources/node": "sources/node.svg",
    "sources/packagename": "sources/packagename.svg",
    "sources/pacman": "sources/pacman.svg",
    "sources/pipx": "sources/pipx.svg",
    "sources/version": "sources/version.svg",
    "status/nosignal": "status/nosignal.png",
    "status/low": "status/signal-low.png",
    "status/medium": "status/signal-medium.png",
    "status/high": "status/signal-high.png",
    "toolbar/addBundle": "toolbar/addBundle.svg",
    "toolbar/install_from_file": "toolbar/install_from_file.svg",
    "toolbar/insatllwithsudo": "toolbar/insatllwithsudo.svg",
    "toolbar/list": "toolbar/list.svg",
    "toolbar/news": "toolbar/news.svg",
    "toolbar/shield": "toolbar/shield.svg",
    "toolbar/view": "toolbar/view.svg",
    "ui/arrow-up-circle": "ui/arrow-up-circle.svg",
    "ui/bell": "ui/bell.svg",
    "ui/bell-ring": "ui/bell-ring.svg",
    "ui/book": "ui/book.svg",
    "ui/box": "ui/box.svg",
    "ui/buymeacoffee": "ui/buymeacoffee.svg",
    "ui/calendar": "ui/calendar.svg",
    "ui/camera": "ui/camera.svg",
    "ui/check": "ui/check.svg",
    "ui/check-line": "ui/check-line.svg",
    "ui/chevron_down": "ui/chevron_down.svg",
    "ui/chevron_up": "ui/chevron_up.svg",
    "ui/clean": "ui/clean.svg",
    "ui/clear": "ui/clear.svg",
    "ui/cloud": "ui/cloud.svg",
    "ui/coffee": "ui/coffee.svg",
    "ui/copy": "ui/copy.svg",
    "ui/createBundle": "ui/createBundle.svg",
    "ui/database": "ui/database.svg",
    "ui/export": "ui/export.svg",
    "ui/file-text": "ui/file-text.svg",
    "ui/gear": "ui/gear.svg",
    "ui/git-branch": "ui/git-branch.svg",
    "ui/globe": "ui/globe.svg",
    "ui/heart": "ui/heart.svg",
    "ui/import": "ui/import.svg",
    "ui/installed": "ui/installed.svg",
    "ui/key": "ui/key.svg",
    "ui/layers": "ui/layers.svg",
    "ui/list-checks": "ui/list-checks.svg",
    "ui/minus": "ui/minus.svg",
    "ui/monitor": "ui/monitor.svg",
    "ui/news-line": "ui/news-line.svg",
    "ui/nowrap": "ui/nowrap.svg",
    "ui/package": "ui/package.svg",
    "ui/palette": "ui/palette.svg",
    "ui/plus": "ui/plus.svg",
    "ui/refresh": "ui/refresh.svg",
    "ui/refresh-cw": "ui/refresh-cw.svg",
    "ui/refreshdb": "ui/refreshdb.svg",
    "ui/repo": "ui/repo.svg",
    "ui/save": "ui/save.svg",
    "ui/search": "ui/search.svg",
    "ui/shield": "ui/shield.svg",
    "ui/shield-alert": "ui/shield-alert.svg",
    "ui/signal": "ui/signal.svg",
    "ui/sliders": "ui/sliders.svg",
    "ui/sparkles": "ui/sparkles.svg",
    "ui/terminal": "ui/terminal.svg",
    "ui/terminal-line": "ui/terminal-line.svg",
    "ui/timer": "ui/timer.svg",
    "ui/trash": "ui/trash.svg",
    "ui/trending-up": "ui/trending-up.svg",
    "ui/update12": "ui/update12.svg",
    "ui/updateall": "ui/updateall.svg",
    "ui/users": "ui/users.svg",
    "ui/wrap": "ui/wrap.svg",
    "ui/wrench": "ui/wrench.svg",
}

SOURCE_ICONS = {
    "pacman": "sources/pacman",
    "AUR": "sources/aur",
    "Flatpak": "sources/flatpak",
    "npm": "sources/node",
    "Firmware": "sources/firmware",
    "pipx": "sources/pipx",
}

BRAND_ICON_CANDIDATES = (
    "app/icon",
    "app/logo",
    "NeoarchLogo.svg",
    "brand/neoarch.svg",
    "brand/neoarch.png",
    "discover/logo.svg",
    "discover/logo1.svg",
    "discover/logo1.png",
    "app",
)

_BRAND_PRO_CANDIDATES = (
    "app/icon-pro",
    "app/logo-pro",
)

_brand_icon = ""
_brand_logo = ""


def set_brand_assets(icon: str = "", logo: str = "") -> None:
    """Select themed brand artwork, or clear it for the default assets."""
    global _brand_icon, _brand_logo
    _brand_icon = str(icon or "").strip()
    _brand_logo = str(logo or "").strip()


def set_brand_pro(enabled: bool) -> None:
    """Select the Pro-branded logo assets for the active theme."""
    if enabled:
        set_brand_assets("app/icon-pro", "app/logo-pro")
    else:
        set_brand_assets()


def icon_path(name: str) -> str:
    """Return the absolute path for a logical icon name or relative path."""
    if not name:
        return str(ICONS_DIR)
    if os.path.isabs(name):
        return name
    return str(ICONS_DIR / ICON_PATHS.get(name, name))


def source_icon_path(source: str) -> str:
    """Return the icon path for a package source, with a safe fallback."""
    return icon_path(SOURCE_ICONS.get(source, "sources/packagename"))


def status_icon_path(state: str) -> str:
    """Return the signal-status icon path for ``nosignal``/``low``/``medium``/``high``."""
    return icon_path(f"status/{state}")


def brand_icon_candidates() -> list[str]:
    """Return brand/logo candidates in preference order."""
    names = BRAND_ICON_CANDIDATES
    if _brand_icon:
        names = (_brand_icon,) + names
    elif _brand_logo:
        names = _BRAND_PRO_CANDIDATES + names
    return [icon_path(name) for name in names]


def brand_icon_path() -> str:
    """Return the first existing brand icon, or the last candidate."""
    candidates = brand_icon_candidates()
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[-1]


def brand_logo_path() -> str:
    """Return the horizontal sidebar/About logo for the active brand."""
    name = _brand_logo or "app/logo"
    path = icon_path(name)
    return path if os.path.exists(path) else icon_path("app/logo")


def has_icon(name: str) -> bool:
    return os.path.isfile(icon_path(name))


@lru_cache(maxsize=512)
def render_pixmap(name: str, size: int, color: str | None = None) -> QPixmap:
    """Render an icon to a square pixmap, tinting SVGs when ``color`` is set."""
    path = icon_path(name)
    size = int(size)
    if not os.path.exists(path):
        return QPixmap()

    if path.lower().endswith(".svg"):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(path)
        if not renderer.isValid():
            return QPixmap()
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, size, size))
        if color:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(QRectF(0, 0, size, size), QColor(color))
        painter.end()
        return pixmap

    pixmap = QPixmap(path)
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


@lru_cache(maxsize=512)
def render_icon(name: str, size: int, color: str | None = None) -> QIcon:
    """Render an icon to a ``QIcon``."""
    path = icon_path(name)
    if not path.lower().endswith(".svg"):
        return QIcon(path)
    pixmap = render_pixmap(name, size, color)
    return QIcon(pixmap) if not pixmap.isNull() else QIcon()
