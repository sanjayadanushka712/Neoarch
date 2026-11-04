"""Theme definitions and loading for NeoArch.

Built-in themes live in ``assets/themes/*.json``.  Users can drop their own
``*.json`` files into one of the search paths below; later directories win,
so a user theme can override a built-in with the same ``id``.

A theme file only needs the values it wants to change.  Missing colors are
inherited from the Dark theme, which makes small accent-only themes possible.
"""

from __future__ import annotations

import hashlib
import hmac
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
    "brand_assets_for_theme",
    "get_theme_background",
    "get_theme_data",
    "get_theme_effects",
    "is_theme_locked",
    "FREE_PRO_THEMES",
    "PRO_UNLOCK_HASHES",
    "UNLOCKED_PRO_SETTING",
    "normalise_unlocked_themes",
    "theme_glow_enabled",
    "verify_theme_unlock_code",
    "load_themes",
    "PRO_TIER",
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
DEFAULT_THEME_ID = "neoarch-pro-endeavour"
PRO_TIER = "pro"
# These Pro themes stay available to everyone.  The rest of the Pro
# collection can be unlocked with the per-theme passwords below; unlocked
# ids are persisted in the main settings file.  Only salted hashes ship.
FREE_PRO_THEMES = frozenset({
    "neoarch-pro",
    "neoarch-pro-endeavour",
    "neoarch-pro-v4",
})
UNLOCKED_PRO_SETTING = "unlocked_pro_themes"
# Only salted PBKDF2 hashes are stored here; plaintext codes never ship.
PRO_UNLOCK_HASHES = {
    "neoarch-pro-evergreen":
        "pbkdf2_sha256$600000$c332b53fe6058229f018085e12ae138d$dd0fb331d4b73603a7edf3acdf8e6c022fabe01933745761c544bdc523f6cdba",
    "neoarch-pro-ember":
        "pbkdf2_sha256$600000$42c72c9cb734d77cee3768d15d134dbd$c38727abf6e9c5179aa9acb8dbd95036e24c2c1414ad124fb5f1750db58abf63",
    "neoarch-pro-glacier":
        "pbkdf2_sha256$600000$4e0997c032f456f2718329f913625ddb$74da07258bd9780a596d5bef5517502a4704e9da4d118ef4664cc981207c62b8",
    "neoarch-pro-aero":
        "pbkdf2_sha256$600000$41c1da7889c543bf2e749694e6d8c11a$73b55855fe1ae905c76b538f76b54859f57f5507403628a3178741407fe3fbd8",
    "neoarch-pro-lagoon":
        "pbkdf2_sha256$600000$dff600520dfd4424972ca77f788fe84d$384874048d1cf3ea8294fea81f2b53320ef3391a4c03ea88d1d0b260536f44ba",
    "neoarch-pro-moss":
        "pbkdf2_sha256$600000$cff70a88c8acbfa85eb585663c22fc28$0eee9d027bb6f89fb42a1aee4e185a5fdf9357ce03dcc4b437ecbfaf1ef317f5",
    "neoarch-pro-sakura":
        "pbkdf2_sha256$600000$f39db6eec64d681c5d79084a8a4e1828$5690762c8f3aef629f58b97bbdea686a3fa8b277f90e9445fb1e3b5081838a4a",
    "neoarch-pro-crystal":
        "pbkdf2_sha256$600000$b7a9bf8359ece5fe3c385cd717687c13$cd4aebadd2619cddd103c4068c1b318b687c7cbdcd666eec2f17bb1baaaacd40",
    "neoarch-pro-halloween":
        "pbkdf2_sha256$600000$1ad2ea6473af6711318ea7d60f681b54$304011c7d0d1befbb9eb5ed4fa5395479686db05a236b44e540ee2cac4ae8e1e",
}


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
        "tier": "standard",
        "background": None,
        "effects": None,
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


def brand_assets_for_theme(theme: dict | None) -> tuple[str, str]:
    """Return the icon/logo asset names declared by ``theme``.

    Any theme may override its brand artwork.  Pro themes without explicit
    artwork still fall back to the bundled Pro icon/logo.
    """
    if not isinstance(theme, dict):
        return "", ""
    icon = str(theme.get("brand_icon") or "").strip()
    logo = str(theme.get("brand_logo") or "").strip()
    if theme.get("tier") == PRO_TIER:
        icon = icon or "app/icon-pro"
        logo = logo or "app/logo-pro"
    return icon, logo


def normalise_unlocked_themes(values) -> frozenset[str]:
    """Return a clean set of unlocked theme ids from a settings value."""
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(
        str(value).strip() for value in values
        if isinstance(value, str) and str(value).strip()
    )


def verify_theme_unlock_code(theme_id: str, code) -> bool:
    """Verify a password against the stored PBKDF2 hash for a Pro theme."""
    encoded = PRO_UNLOCK_HASHES.get(theme_id)
    if not encoded or code is None:
        return False
    try:
        scheme, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(expected_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            str(code).strip().encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def is_theme_locked(theme_id: str, unlocked=None) -> bool:
    """Return True when a Pro theme must not be applied without an unlock.

    Free Pro themes, explicitly unlocked Pro themes, and every
    standard/system theme remain selectable.
    """
    if theme_id == SYSTEM_THEME_ID or theme_id in FREE_PRO_THEMES:
        return False
    if theme_id in normalise_unlocked_themes(unlocked):
        return False
    theme = THEMES.get(theme_id)
    return bool(theme and theme.get("tier") == PRO_TIER)


def get_theme_effects(theme_id: str) -> dict | None:
    """Return the optional visual effects declared by a concrete theme."""
    if theme_id == SYSTEM_THEME_ID:
        return None
    theme = THEMES.get(theme_id)
    if not theme:
        return None
    effects = theme.get("effects")
    return dict(effects) if isinstance(effects, dict) else None


def theme_glow_enabled(theme_id: str | None) -> bool:
    """True when a theme's glow effect is enabled by default."""
    effects = get_theme_effects(theme_id) if theme_id else None
    glow = (effects or {}).get("glow")
    return bool(isinstance(glow, dict) and glow.get("enabled", True))


def get_theme_background(theme_id: str) -> dict | None:
    """Return the optional wallpaper configuration for a concrete theme."""
    if theme_id == SYSTEM_THEME_ID:
        return None
    theme = THEMES.get(theme_id)
    if not theme:
        return None
    background = theme.get("background")
    return dict(background) if isinstance(background, dict) else None


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
        "tier": "standard",
        "background": None,
        "effects": None,
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
    for key in ("brand_icon", "brand_logo"):
        value = str(data.get(key) or "").strip()
        if not value or os.path.isabs(value):
            continue
        candidate = path.parent / value
        if candidate.is_file():
            data[key] = str(candidate)
    background = data.get("background")
    if isinstance(background, dict):
        image = str(background.get("image") or "").strip()
        if image:
            image_path = Path(image).expanduser()
            if not image_path.is_absolute():
                image_path = path.parent / image_path
            background = dict(background)
            background["image"] = str(image_path)
            data["background"] = background
    return data


def _normalise_effects(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    glow_raw = raw.get("glow")
    if not isinstance(glow_raw, dict):
        return None
    try:
        width = float(glow_raw.get("width", 1.0))
    except (TypeError, ValueError):
        width = 1.0
    try:
        opacity = float(glow_raw.get("opacity", 0.55))
    except (TypeError, ValueError):
        opacity = 0.55
    return {
        "glow": {
            "enabled": bool(glow_raw.get("enabled", True)),
            "color": str(glow_raw.get("color") or "").strip(),
            "width": max(0.5, min(4.0, width)),
            "opacity": max(0.0, min(1.0, opacity)),
        }
    }


def _normalise_background(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    image = str(raw.get("image") or "").strip()
    if not image:
        return None
    try:
        blur = int(float(raw.get("blur", 0) or 0))
    except (TypeError, ValueError):
        blur = 0
    try:
        opacity = float(raw.get("opacity", 1.0))
    except (TypeError, ValueError):
        opacity = 1.0
    return {
        "image": image,
        "fit": str(raw.get("fit") or "cover").strip().lower(),
        "position": str(raw.get("position") or "center").strip().lower(),
        "blur": max(0, min(64, blur)),
        "opacity": max(0.0, min(1.0, opacity)),
        "scrim": str(raw.get("scrim") or "").strip(),
        "mode": str(raw.get("mode") or "image").strip().lower(),
    }


def _normalise(theme_id: str, raw: dict, base: dict | None) -> dict:
    base = base or {}
    colors = dict(base.get("colors", {}))
    colors.update(raw.get("colors", {}))
    source_colors = dict(base.get("source_colors", {}))
    source_colors.update(raw.get("source_colors", {}))
    tier = str(raw.get("tier") or "standard").strip().lower()
    return {
        "id": theme_id,
        "name": str(raw.get("name") or theme_id.replace("-", " ").title()),
        "description": str(raw.get("description") or ""),
        "is_dark": bool(raw.get("is_dark", base.get("is_dark", True))),
        "coming_soon": bool(raw.get("coming_soon", False)),
        "tier": tier if tier else "standard",
        "brand_icon": str(raw.get("brand_icon") or "").strip(),
        "brand_logo": str(raw.get("brand_logo") or "").strip(),
        "background": _normalise_background(raw.get("background")),
        "effects": _normalise_effects(raw.get("effects")),
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

    def _owner_settings(self):
        """Return settings from the owning app, falling back to disk early."""
        try:
            parent = self.parent()
        except RuntimeError:
            return None
        if parent is None:
            return None
        settings = getattr(parent, "settings", None)
        if isinstance(settings, dict):
            return settings
        try:
            from neoarch.backend.services.settings import load_settings
            return load_settings()
        except Exception:
            return None

    def unlocked_theme_ids(self):
        """Return Pro themes unlocked in the owning app's saved settings."""
        settings = self._owner_settings()
        if settings is None:
            return frozenset()
        return normalise_unlocked_themes(
            settings.get(UNLOCKED_PRO_SETTING, ()))

    def trial_status(self, theme_id):
        """Return the local trial status for a locked Pro theme."""
        settings = self._owner_settings()
        if settings is None:
            from neoarch.backend.services.pro_trials import TrialStatus
            return TrialStatus("tampered", 0)
        from neoarch.backend.services.pro_trials import trial_status
        return trial_status(settings, theme_id)

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
        locked = is_theme_locked(resolved_id, self.unlocked_theme_ids())
        if (theme is None or theme.get("coming_soon")
                or (locked and not self.trial_status(resolved_id).usable)):
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
        if self.apply_theme(self._current_id):
            return True
        if self._current_id != DARK_THEME_ID:
            return self.apply_theme(DARK_THEME_ID)
        return False

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
            with open(self._settings_path, "w") as f:
                json.dump({"theme": self._current_id}, f)
        except Exception:
            pass

    def load_saved(self):
        """Load the saved theme from disk, falling back to the default theme."""
        theme_id = DEFAULT_THEME_ID
        try:
            with open(self._settings_path) as f:
                data = json.load(f)
                saved = data.get("theme", DEFAULT_THEME_ID)
                if saved == SYSTEM_THEME_ID or saved in THEMES:
                    theme_id = saved
        except Exception:
            pass
        if not self.apply_theme(theme_id) and theme_id != DARK_THEME_ID:
            self.apply_theme(DARK_THEME_ID)
