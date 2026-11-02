"""Icon and style utilities mixin for the main window.

Provides SVG icon rendering with caching, source-specific icons,
checkbox styling, drop shadows, and related utilities.
"""

import os
import shutil
import subprocess

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QPainter, QIcon, QImage

from neoarch.frontend.icon_registry import render_icon, render_pixmap, source_icon_path
from neoarch.frontend.tokens import Colors, Fonts, SourceColors, icon_tint


def _build_window_icon(icon_path: str) -> QIcon:
    try:
        icon = QIcon()
        if not os.path.exists(icon_path):
            return icon
        ext = os.path.splitext(icon_path)[1].lower()
        if ext == ".svg":
            for sz in (32, 64, 256):
                pm = render_pixmap(icon_path, sz)
                if not pm.isNull():
                    icon.addPixmap(pm)
            return icon if not icon.isNull() else QIcon(icon_path)
        base = QPixmap(icon_path)
        if base.isNull():
            return QIcon(icon_path)
        try:
            img = base.toImage().convertToFormat(QImage.Format.Format_ARGB32)
            w, h = img.width(), img.height()
            min_x, min_y = w, h
            max_x, max_y = -1, -1
            for y in range(h):
                for x in range(w):
                    if img.pixelColor(x, y).alpha() > 0:
                        if x < min_x: min_x = x
                        if y < min_y: min_y = y
                        if x > max_x: max_x = x
                        if y > max_y: max_y = y
            if max_x >= min_x and max_y >= min_y:
                base = base.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
        except Exception:
            pass
        icon.addPixmap(base)
        return icon
    except Exception:
        return QIcon(icon_path)


class _IconsMixin:
    def get_fallback_icon(self, icon_path):
        if "sources" in icon_path or "ui" in icon_path:
            return "\U0001f50d"
        elif "updates" in icon_path:
            return "\u2b06\ufe0f"
        elif "installed" in icon_path:
            return "\U0001f4e6"
        elif "local" in icon_path or "bundles" in icon_path:
            return "\U0001f381"
        elif "settings" in icon_path:
            return "\u2699\ufe0f"
        elif "docker" in icon_path.lower():
            return "\U0001f433"
        else:
            return "\U0001f4e6"

    def get_source_icon(self, source, size=18):
        source_colors = SourceColors
        icon_path = source_icon_path(source)
        try:
            cache = getattr(self, "_source_icon_cache", None)
            if isinstance(cache, dict):
                key = (source, int(size))
                cached = cache.get(key)
                if cached is not None and not cached.isNull():
                    return cached
        except Exception:
            pass

        try:
            icon = render_icon(icon_path, size)
            if icon.isNull():
                color = source_colors.get(source, Colors.TEXT_2)
                pm = QPixmap(size, size)
                pm.fill(Qt.GlobalColor.transparent)
                p = QPainter(pm)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(color))
                margin = size // 4
                p.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
                p.end()
                icon = QIcon(pm)

            try:
                if isinstance(getattr(self, "_source_icon_cache", None), dict):
                    self._source_icon_cache[(source, int(size))] = icon
            except Exception:
                pass
            return icon
        except Exception:
            return QIcon()

    def get_svg_icon(self, icon_path, size=18, tint=None):
        resolved_tint = tint or icon_tint()
        key = (os.path.abspath(icon_path), int(size), str(resolved_tint))
        try:
            cache = getattr(self, "_icon_cache", None)
            if isinstance(cache, dict):
                cached = cache.get(key)
                if cached is not None and not cached.isNull():
                    return cached
        except Exception:
            pass

        try:
            icon = render_icon(icon_path, size, resolved_tint)

            try:
                if isinstance(getattr(self, "_icon_cache", None), dict):
                    self._icon_cache[key] = icon
            except Exception:
                pass
            return icon
        except Exception:
            return QIcon()

    def get_source_accent(self, source):
        return SourceColors.get(source, Colors.ACCENT)

    def apply_checkbox_accent(self, checkbox, source):
        hex_color = self.get_source_accent(source)
        c = QColor(hex_color)
        r, g, b = c.red(), c.green(), c.blue()
        checkbox.setStyleSheet(
            f"""
            QCheckBox#tableCheckbox {{
                color: {Colors.TEXT};
                font-size: {Fonts.BASE};
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox#tableCheckbox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 11px;
                border: 2px solid rgba({r}, {g}, {b}, 0.35);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {Colors.GLASS_40_90},
                    stop:1 {Colors.GLASS_2_90});
            }}
            QCheckBox#tableCheckbox::indicator:checked {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {hex_color},
                    stop:1 rgba({r//2}, {g//2}, {b//2}, 1));
                border: 2px solid {hex_color};
            }}
            QCheckBox#tableCheckbox::indicator:hover {{
                border-color: rgba({r}, {g}, {b}, 0.8);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {Colors.GLASS_50_90},
                    stop:1 {Colors.GLASS_2_90});
            }}
            """
        )

    def ensure_flathub_user_remote(self):
        try:
            result = subprocess.run([
                shutil.which("flatpak") or "flatpak", "--user", "remotes"
            ], capture_output=True, text=True, timeout=10, check=False)
            if result.returncode != 0 or "flathub" not in (result.stdout or ""):
                subprocess.run([
                    shutil.which("flatpak") or "flatpak", "--user", "remote-add", "--if-not-exists",
                    "flathub", "https://flathub.org/repo/flathub.flatpakrepo"
                ], capture_output=True, text=True, timeout=30, check=False)
        except Exception:
            pass
        try:
            self._flathub_checked = True
        except Exception:
            pass
