"""Theme definitions and loading for NeoArch.

Built-in themes live in ``assets/themes/*.json``.  Users can drop their own
``*.json`` files into one of the search paths below; later directories win,
so a user theme can override a built-in with the same ``id``.

A theme file only needs the values it wants to change.  Missing colors are
inherited from the Dark theme, which makes small accent-only themes possible.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from neoarch.resources.paths import ASSETS_DIR

__all__ = [
    "DARK_THEME_ID",
    "DEFAULT_THEME_ID",
    "SYSTEM_THEME_ID",
    "THEMES",
    "THEME_DIRS",
    "ThemeManager",
    "get_theme_data",
    "load_themes",
    "reload_themes",
    "system_font_families",
    "system_metric_scale",
    "system_scrollbar_width",
    "system_theme_id",
    "theme_search_paths",
]

BUILTIN_THEME_DIR = ASSETS_DIR / "themes"
DARK_THEME_ID = "dark"
SYSTEM_THEME_ID = "system"
DEFAULT_THEME_ID = SYSTEM_THEME_ID


def system_theme_id() -> str:
    """Return the concrete theme matching the operating system appearance."""
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPalette
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return DARK_THEME_ID
        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Light:
            return "light" if "light" in THEMES else DARK_THEME_ID
        if scheme == Qt.ColorScheme.Dark:
            return DARK_THEME_ID
        window = app.palette().color(QPalette.ColorRole.Window)
        if window.lightness() > 127:
            return "light" if "light" in THEMES else DARK_THEME_ID
    except Exception:
        pass
    return DARK_THEME_ID


def _hex(color: QColor) -> str:
    """Return an uppercase ``#RRGGBB`` string for a QColor."""
    return color.name(QColor.NameFormat.HexRgb).upper()


def _css(color: QColor) -> str:
    """Return a CSS color, preserving QColor alpha when present."""
    from neoarch.frontend import tokens

    return tokens.css_color(color)


def _mix(first: QColor, second: QColor, weight: float) -> QColor:
    """Blend two colors; ``weight`` 0 is first, 1 is second."""
    weight = max(0.0, min(1.0, weight))
    inverse = 1.0 - weight
    return QColor(
        round(first.red() * inverse + second.red() * weight),
        round(first.green() * inverse + second.green() * weight),
        round(first.blue() * inverse + second.blue() * weight),
    )


def _shift_lightness(color: QColor, amount: float) -> QColor:
    """Lighten (positive) or darken (negative) a color in HSL space."""
    hue, saturation, lightness, alpha = color.getHslF()
    if hue < 0:
        hue = 0.0
    return QColor.fromHslF(
        hue,
        max(0.0, min(1.0, saturation)),
        max(0.0, min(1.0, lightness + amount)),
        max(0.0, min(1.0, alpha)),
    )


def _relative_luminance(color: QColor) -> float:
    """Return WCAG relative luminance for an opaque color."""
    def channel(value: int) -> float:
        value = value / 255.0
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * channel(color.red())
        + 0.7152 * channel(color.green())
        + 0.0722 * channel(color.blue())
    )


def _contrast_ratio(first: QColor, second: QColor) -> float:
    """Return the WCAG contrast ratio between two opaque colors."""
    lum_a = _relative_luminance(first)
    lum_b = _relative_luminance(second)
    lighter = max(lum_a, lum_b)
    darker = min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def _composite(foreground: QColor, background: QColor) -> QColor:
    """Composite a translucent foreground over an opaque background."""
    alpha = foreground.alphaF()
    inverse = 1.0 - alpha
    return QColor(
        round(foreground.red() * alpha + background.red() * inverse),
        round(foreground.green() * alpha + background.green() * inverse),
        round(foreground.blue() * alpha + background.blue() * inverse),
    )


def _border_alpha(
        background: QColor,
        foreground: QColor,
        start: float,
        minimum_ratio: float) -> float:
    """Raise a border alpha until it is visible against the background."""
    alpha = start
    while alpha < 0.50:
        candidate = QColor(foreground)
        candidate.setAlphaF(alpha)
        if _contrast_ratio(
                _composite(candidate, background), background) >= minimum_ratio:
            return alpha
        alpha += 0.02
    return 0.50


def _palette_color(palette, role_name: str, fallback: QColor) -> QColor:
    """Read a QPalette role, falling back to a theme token."""
    try:
        from PyQt6.QtGui import QPalette

        color = palette.color(getattr(QPalette.ColorRole, role_name))
        if color.isValid() and color.alpha() > 0:
            return color
    except Exception:
        pass
    return fallback


def _system_palette_colors(base: dict) -> dict:
    """Build a full token palette from the live QPalette.

    Only the neutral surfaces, text, borders, and accent families are
    replaced. Semantic colors and glass tokens keep the light/dark base so
    success/warning/error states stay recognizable.
    """
    from neoarch.frontend import tokens

    base_colors = dict(base.get("colors", {}))
    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return base_colors
        palette = app.palette()
    except Exception:
        return base_colors

    window = _palette_color(
        palette, "Window", QColor(base_colors.get("BG") or "black"))
    base_bg = _palette_color(
        palette, "Base", QColor(base_colors.get("SURFACE") or "black"))
    alternate = _palette_color(
        palette, "AlternateBase",
        QColor(base_colors.get("SURFACE_2") or "black"))
    button = _palette_color(
        palette, "Button", QColor(base_colors.get("CARD") or "black"))
    window_text = _palette_color(
        palette, "WindowText", QColor(base_colors.get("TEXT") or "white"))
    text = _palette_color(palette, "Text", window_text)
    highlight = _palette_color(
        palette, "Highlight", QColor(base_colors.get("ACCENT") or "blue"))
    highlighted_text = _palette_color(
        palette, "HighlightedText",
        QColor(base_colors.get("TEXT_ON_ACCENT") or "white"))
    placeholder = _palette_color(
        palette, "PlaceholderText", _mix(window_text, window, 0.58))
    mid = _palette_color(
        palette, "Mid", _mix(window_text, window, 0.38))
    midlight = _palette_color(
        palette, "Midlight", _mix(window, window_text, 0.10))
    dark = _palette_color(
        palette, "Dark", _mix(window_text, window, 0.68))
    light = _palette_color(
        palette, "Light", _mix(window, window_text, 0.18))

    border_alpha = _border_alpha(window, window_text, 0.10, 1.28)
    input_alpha = _border_alpha(base_bg, window_text, 0.14, 1.36)
    hover_alpha = _border_alpha(base_bg, window_text, 0.18, 1.44)

    colors = dict(base_colors)
    colors.update({
        "BG": _hex(window),
        "BG_SECONDARY": _hex(_mix(window, alternate, 0.55)),
        "SURFACE": _hex(base_bg),
        "SURFACE_2": _hex(_mix(base_bg, button, 0.55)),
        "SURFACE_3": _hex(_mix(button, mid, 0.55)),
        "CARD": _hex(base_bg),
        "CARD_HOVER": _hex(_mix(base_bg, window_text, 0.04)),
        "INPUT_BG": _hex(base_bg),
        "INPUT_BG_FOCUS": _hex(_mix(base_bg, highlight, 0.04)),
        "SIDEBAR": _hex(_mix(window, alternate, 0.35)),
        "BORDER": tokens.alpha_css(window_text, border_alpha),
        "BORDER_INPUT": tokens.alpha_css(window_text, input_alpha),
        "BORDER_HOVER": tokens.alpha_css(window_text, hover_alpha),
        "BORDER_FOCUS": tokens.alpha_css(highlight, 0.55),
        "BORDER_STRONG": tokens.alpha_css(window_text, 0.25),
        "TEXT": _css(text if text.isValid() else window_text),
        "TEXT_2": _css(_mix(window_text, window, 0.40)),
        "TEXT_3": _css(placeholder if placeholder.isValid()
                       else _mix(window_text, window, 0.60)),
        "TEXT_ON_ACCENT": _css(highlighted_text),
        "ACCENT": _hex(highlight),
        "ACCENT_HOVER": _hex(_shift_lightness(highlight, 0.06)),
        "ACCENT_PRESSED": _hex(_shift_lightness(highlight, -0.06)),
        "ACCENT_SOFT": tokens.alpha_css(highlight, 0.12),
        "ACCENT_BORDER": tokens.alpha_css(highlight, 0.25),
        "ACCENT_BORDER_STRONG": tokens.alpha_css(highlight, 0.35),
        "NEON": _hex(highlight),
    })

    # Keep the accent/overlay/neon alpha families in sync with the live
    # system accent and text color.
    for key in list(colors):
        if key.startswith("ACCENT_"):
            try:
                alpha = int(key.rsplit("_", 1)[1]) / 100.0
            except (ValueError, IndexError):
                continue
            colors[key] = tokens.alpha_css(highlight, alpha)
        elif key.startswith("OVERLAY_"):
            try:
                alpha = int(key.rsplit("_", 1)[1]) / 100.0
            except (ValueError, IndexError):
                continue
            colors[key] = tokens.alpha_css(window_text, alpha)
        elif key.startswith("NEON_"):
            try:
                alpha = int(key.rsplit("_", 1)[1]) / 100.0
            except (ValueError, IndexError):
                continue
            colors[key] = tokens.alpha_css(highlight, alpha)

    # Darker/lighter roles are available for components that need them.
    colors.setdefault("TEXT_2", _css(mid))
    colors.setdefault("TEXT_3", _css(dark))
    colors.setdefault("SURFACE_3", _css(midlight))
    colors.setdefault("BORDER_STRONG", tokens.alpha_css(light, 0.25))
    return colors


def _system_theme_data(resolved_id: str, base: dict | None) -> dict | None:
    """Return the virtual System theme with live OS colors."""
    if base is None:
        return None
    colors = _system_palette_colors(base)
    try:
        is_dark = QColor(colors.get("BG", "")).lightness() < 128
    except Exception:
        is_dark = bool(base.get("is_dark", True))
    return {
        **base,
        "id": SYSTEM_THEME_ID,
        "name": "System",
        "description": (
            "Follow the operating system appearance "
            f"(currently {base['name']})"
        ),
        "is_dark": is_dark,
        "coming_soon": False,
        "colors": colors,
    }


def system_font_families() -> tuple[str, str] | None:
    """Return CSS family lists for the OS UI font and fixed-width font."""
    try:
        from PyQt6.QtGui import QFontDatabase
        from PyQt6.QtWidgets import QApplication
        from neoarch.frontend import tokens

        if QApplication.instance() is None:
            return None
        general = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.GeneralFont)
        fixed = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.FixedFont)
        family = general.family().strip()
        mono = fixed.family().strip()
        if not family:
            family = QApplication.instance().font().family().strip()
        if not mono:
            mono = family
        if not family:
            return None

        def quoted(name: str) -> str:
            return "'" + name.replace("\\", "\\\\").replace("'", "\\'") + "'"

        return (
            f"{quoted(family)}, {tokens.Fonts.DEFAULT_FAMILY}",
            f"{quoted(mono)}, {tokens.Fonts.DEFAULT_MONO}",
        )
    except Exception:
        return None


def system_font_scale() -> float:
    """Return a safe UI size scale based on the OS font point size."""
    try:
        from PyQt6.QtGui import QFontDatabase, QFontInfo
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is None:
            return 1.0
        font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.GeneralFont)
        point_size = QFontInfo(font).pointSizeF()
        if point_size <= 0:
            point_size = font.pointSizeF()
        if point_size <= 0:
            return 1.0
        return max(0.85, min(point_size / 9.75, 1.20))
    except Exception:
        return 1.0


def system_metric_scale() -> float:
    """Return a conservative UI metric scale for the current platform."""
    import sys

    if sys.platform.startswith("win"):
        return 0.85
    if sys.platform == "darwin":
        return 1.0
    return 0.9


def system_scrollbar_width() -> int:
    """Return a system-like scrollbar width, clamped for the UI."""
    try:
        from PyQt6.QtWidgets import QApplication, QStyle

        app = QApplication.instance()
        if app is None:
            return 8
        extent = app.style().pixelMetric(
            QStyle.PixelMetric.PM_ScrollBarExtent)
        return max(8, min(int(extent), 14))
    except Exception:
        return 8


def get_theme_data(theme_id: str) -> dict | None:
    """Return display data for a theme, including the virtual system theme."""
    if theme_id == SYSTEM_THEME_ID:
        resolved = system_theme_id()
        base = THEMES.get(resolved) or THEMES.get(DARK_THEME_ID)
        return _system_theme_data(resolved, base)
    return THEMES.get(theme_id)


def theme_search_paths() -> list[Path]:
    """Return theme directories in increasing priority order."""
    return [
        BUILTIN_THEME_DIR,
        Path.home() / ".local" / "share" / "neoarch" / "themes",
        Path.home() / ".config" / "neoarch" / "themes",
    ]


THEME_DIRS = theme_search_paths()


def _tokens_fallback() -> dict:
    """Build a Dark theme from the live token defaults.

    This keeps the app usable if the built-in JSON is missing (for example a
    broken package) without duplicating the whole palette here.
    """
    from neoarch.frontend import tokens

    colors = {
        key: value
        for key, value in vars(tokens.Colors).items()
        if key.isupper() and isinstance(value, str)
    }
    return {
        "id": DARK_THEME_ID,
        "name": "Dark",
        "description": "Default premium dark theme",
        "is_dark": True,
        "coming_soon": False,
        "colors": colors,
        "source_colors": dict(tokens.SourceColors),
    }


def _read_theme_file(path: Path) -> dict | None:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    colors = data.get("colors", {})
    source_colors = data.get("source_colors", {})
    if not isinstance(colors, dict) or not isinstance(source_colors, dict):
        return None
    theme_id = str(data.get("id") or path.stem).strip()
    if not theme_id:
        return None
    data["id"] = theme_id
    return data


def _normalise(theme_id: str, raw: dict, base: dict | None) -> dict:
    base = base or {}
    colors = dict(base.get("colors", {}))
    colors.update(raw.get("colors", {}))
    source_colors = dict(base.get("source_colors", {}))
    source_colors.update(raw.get("source_colors", {}))
    return {
        "id": theme_id,
        "name": str(raw.get("name") or theme_id.replace("-", " ").title()),
        "description": str(raw.get("description") or ""),
        "is_dark": bool(raw.get("is_dark", base.get("is_dark", True))),
        "coming_soon": bool(raw.get("coming_soon", False)),
        "colors": colors,
        "source_colors": source_colors,
    }


def load_themes(dirs: list[Path] | None = None) -> dict[str, dict]:
    """Load built-in and user themes from ``dirs`` (or the default paths)."""
    raw_themes: dict[str, dict] = {}
    for directory in dirs if dirs is not None else theme_search_paths():
        try:
            paths = sorted(Path(directory).glob("*.json"))
        except OSError:
            continue
        for path in paths:
            theme = _read_theme_file(path)
            if theme is not None:
                raw_themes[theme["id"]] = theme

    fallback = _tokens_fallback()
    dark_raw = raw_themes.get(DARK_THEME_ID)
    dark = _normalise(DARK_THEME_ID, dark_raw, fallback) if dark_raw else fallback

    themes = {DARK_THEME_ID: dark}
    for theme_id, raw in raw_themes.items():
        if theme_id in (DARK_THEME_ID, SYSTEM_THEME_ID):
            continue
        themes[theme_id] = _normalise(theme_id, raw, dark)
    return themes


THEMES = load_themes()


def reload_themes() -> dict[str, dict]:
    """Re-scan the theme directories and refresh the shared ``THEMES`` map."""
    THEMES.clear()
    THEMES.update(load_themes())
    return THEMES


def _snapshot_tokens() -> dict:
    """Capture mutable token values before applying a theme."""
    from neoarch.frontend import tokens

    snapshot = {}
    for name in ("Colors", "Fonts", "Radii", "Spacing", "Scrollbar"):
        token_class = getattr(tokens, name)
        snapshot[name] = {
            key: value
            for key, value in vars(token_class).items()
            if key.isupper()
        }
    snapshot["SourceColors"] = dict(tokens.SourceColors)
    return snapshot


def _restore_tokens(snapshot: dict) -> None:
    """Restore mutable token values after a failed theme application."""
    from neoarch.frontend import tokens

    for name, values in snapshot.items():
        if name == "SourceColors":
            tokens.SourceColors.clear()
            tokens.SourceColors.update(values)
            continue
        token_class = getattr(tokens, name)
        for key, value in values.items():
            setattr(token_class, key, value)


class ThemeManager(QObject):
    """Applies themes to the token system and emits change signals."""

    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_id = DEFAULT_THEME_ID
        self._resolved_id = DARK_THEME_ID
        self._system_tracking = False
        self._applying_theme = False
        self._settings_path = os.path.join(
            os.path.expanduser("~"), ".config", "neoarch", "theme.json")
        self._system_update_timer = QTimer(self)
        self._system_update_timer.setSingleShot(True)
        self._system_update_timer.setInterval(150)
        self._system_update_timer.timeout.connect(self._apply_system_update)

    @property
    def current_id(self):
        return self._current_id

    @property
    def resolved_id(self):
        return self._resolved_id

    def _resolve_theme_id(self, theme_id):
        if theme_id == SYSTEM_THEME_ID:
            resolved = system_theme_id()
            return resolved if resolved in THEMES else DARK_THEME_ID
        return theme_id

    def _apply_font_tokens(self, theme_id):
        """Match the OS UI/fixed font in System mode; restore defaults else."""
        from neoarch.frontend import tokens

        if theme_id == SYSTEM_THEME_ID:
            families = system_font_families()
            if families:
                tokens.Fonts.FAMILY, tokens.Fonts.MONO = families
            scale = system_font_scale()
        else:
            tokens.Fonts.FAMILY = tokens.Fonts.DEFAULT_FAMILY
            tokens.Fonts.MONO = tokens.Fonts.DEFAULT_MONO
            scale = 1.0

        for name in tokens.FONT_SIZE_NAMES:
            default = tokens.DEFAULT_FONT_SIZES[name]
            try:
                size = int(str(default).rstrip("px"))
            except (TypeError, ValueError):
                continue
            setattr(tokens.Fonts, name, f"{max(8, round(size * scale))}px")

    def _apply_metric_tokens(self, theme_id):
        """Use platform-like radii, spacing, and scrollbars in System mode."""
        from neoarch.frontend import tokens

        if theme_id == SYSTEM_THEME_ID:
            scale = system_metric_scale()
            width = system_scrollbar_width()
        else:
            scale = 1.0
            width = None

        for name in tokens.RADII_NAMES:
            default = int(tokens.DEFAULT_RADII[name])
            value = max(2, round(default * scale))
            setattr(tokens.Radii, name, str(value))
        for name in tokens.SPACING_NAMES:
            default = int(tokens.DEFAULT_SPACING[name])
            value = max(2, round(default * scale))
            setattr(tokens.Spacing, name, str(value))

        if width is None:
            for name, default in tokens.DEFAULT_SCROLLBAR.items():
                setattr(tokens.Scrollbar, name, default)
            return
        tokens.Scrollbar.WIDTH = str(width)
        tokens.Scrollbar.RADIUS = str(max(3, width // 2))
        tokens.Scrollbar.MARGIN = str(max(2, width // 4))
        tokens.Scrollbar.MIN_LEN = str(max(24, width * 3))

    def apply_theme(self, theme_id):
        """Apply a theme by id and regenerate the QSS blocks."""
        resolved_id = self._resolve_theme_id(theme_id)
        if theme_id == SYSTEM_THEME_ID:
            base = THEMES.get(resolved_id) or THEMES.get(DARK_THEME_ID)
            theme = _system_theme_data(resolved_id, base)
        else:
            theme = THEMES.get(resolved_id)
        if theme is None or theme.get("coming_soon"):
            return False
        previous_id = self._current_id
        previous_resolved = self._resolved_id
        self._current_id = theme_id
        self._resolved_id = resolved_id

        from neoarch.frontend import tokens

        token_snapshot = _snapshot_tokens()
        self._applying_theme = True
        try:
            for key, val in theme["colors"].items():
                if hasattr(tokens.Colors, key):
                    setattr(tokens.Colors, key, val)

            self._apply_font_tokens(theme_id)
            self._apply_metric_tokens(theme_id)

            tokens.SourceColors.clear()
            tokens.SourceColors.update(theme["source_colors"])

            tokens.QSS.regenerate()
            tokens.rebuild_stylesheet()
        except Exception:
            _restore_tokens(token_snapshot)
            self._current_id = previous_id
            self._resolved_id = previous_resolved
            try:
                tokens.QSS.regenerate()
                tokens.rebuild_stylesheet()
            except Exception:
                pass
            raise
        finally:
            self._applying_theme = False

        self._save()
        self.theme_changed.emit(theme_id)
        return True

    def enable_system_tracking(self):
        """Re-apply the system theme when OS colors or fonts change."""
        if self._system_tracking:
            return
        try:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                return
            connected = False
            hints = app.styleHints()
            signal = getattr(hints, "colorSchemeChanged", None)
            if signal is not None:
                signal.connect(self._on_system_color_scheme_changed)
                connected = True
            for name in ("paletteChanged", "fontChanged"):
                signal = getattr(app, name, None)
                if signal is not None:
                    signal.connect(self._on_system_color_scheme_changed)
                    connected = True
            if connected:
                self._system_tracking = True
        except Exception:
            pass

    def _on_system_color_scheme_changed(self, *_args):
        if self._applying_theme:
            return
        if self._current_id == SYSTEM_THEME_ID:
            self._system_update_timer.start()

    def _apply_system_update(self):
        if self._applying_theme:
            return
        if self._current_id == SYSTEM_THEME_ID:
            self.apply_theme(SYSTEM_THEME_ID)

    def reload(self):
        """Reload theme files and re-apply the current theme if possible."""
        reload_themes()
        if self._current_id not in THEMES and self._current_id != SYSTEM_THEME_ID:
            self._current_id = DEFAULT_THEME_ID
        return self.apply_theme(self._current_id)

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
            with open(self._settings_path, "w") as f:
                json.dump({"theme": self._current_id}, f)
        except Exception:
            pass

    def load_saved(self):
        """Load the saved theme from disk, falling back to the system theme."""
        theme_id = DEFAULT_THEME_ID
        try:
            with open(self._settings_path) as f:
                data = json.load(f)
                saved = data.get("theme", DEFAULT_THEME_ID)
                if saved == SYSTEM_THEME_ID or saved in THEMES:
                    theme_id = saved
        except Exception:
            pass
        self.apply_theme(theme_id)
