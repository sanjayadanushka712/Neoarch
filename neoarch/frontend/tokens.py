"""Centralized design tokens for NeoArch.

Single source of truth for ALL colors, fonts, spacing, and radius values.
Every component should import from here instead of defining its own tokens.

Supports dynamic theme switching — call QSS.regenerate() after updating
Colors/Fonts/Radii to rebuild all QSS blocks.

Usage:
    from neoarch.frontend.tokens import T, Colors, Fonts, Radii, Spacing, QSS
"""

__all__ = ["T", "Colors", "Fonts", "Radii", "Spacing", "Scrollbar",
           "SourceColors", "QSS", "DARK_STYLESHEET", "rebuild_stylesheet",
           "qcolor", "icon_tint"]

from PyQt6.QtGui import QColor

from neoarch.frontend.icon_registry import icon_path as _icon_path


def qcolor(value, alpha=None) -> QColor:
    """Build a QColor from a hex token or a CSS ``rgb()``/``rgba()`` token.

    ``alpha`` optionally overrides the token alpha with a 0-255 value.
    """
    if isinstance(value, QColor):
        color = QColor(value)
    else:
        text = str(value).strip()
        lowered = text.lower()
        if lowered.startswith(("rgb(", "rgba(")):
            body = text[text.index("(") + 1:text.rindex(")")]
            parts = [p.strip() for p in body.split(",")]
            r, g, b = (int(round(float(p))) for p in parts[:3])
            a = int(round(float(parts[3]) * 255)) if len(parts) > 3 else 255
            color = QColor(r, g, b, a)
        else:
            color = QColor(text)
    if alpha is not None:
        color.setAlpha(int(alpha))
    return color


def icon_tint() -> str:
    """Default stroke-icon tint: white on dark themes, muted text on light."""
    return Colors.WHITE if qcolor(Colors.BG).lightness() < 128 else Colors.TEXT_2


def alpha_css(color: QColor, alpha: float) -> str:
    """Format a QColor as a CSS alpha color string."""
    return (
        f"rgba({color.red()}, {color.green()}, {color.blue()}, "
        f"{max(0.0, min(1.0, alpha)):.3f})"
    )


def css_color(color: QColor) -> str:
    """Format a QColor as hex, or as alpha CSS when the color has alpha."""
    if color.alpha() < 255:
        return alpha_css(color, color.alpha() / 255.0)
    return color.name(QColor.NameFormat.HexRgb).upper()


# ── Core palette ───────────────────────────────────────────────────

class Colors:
    """All color tokens."""

    # Backgrounds (darkest → lightest)
    BG = "#0C0C0E"
    BG_SECONDARY = "#191A1F"
    SURFACE = "#16171A"
    SURFACE_2 = "#1E1F24"
    SURFACE_3 = "#252730"
    CARD = "#1C1E24"
    CARD_HOVER = "#22242A"
    INPUT_BG = "#121316"
    INPUT_BG_FOCUS = "#141518"
    SIDEBAR = "#0E0E10"

    # Borders
    BORDER = "rgba(255, 255, 255, 0.06)"
    BORDER_INPUT = "rgba(255, 255, 255, 0.08)"
    BORDER_HOVER = "rgba(255, 255, 255, 0.10)"
    BORDER_FOCUS = "rgba(0, 191, 174, 0.5)"
    BORDER_STRONG = "rgba(255, 255, 255, 0.20)"

    # Text
    TEXT = "#EDEDEF"
    TEXT_2 = "#8B8D97"
    TEXT_3 = "#5C5E66"
    TEXT_ON_ACCENT = "#0C0C0E"
    TEXT_ON_WHITE = "#0C0C0E"

    # Primary accent
    ACCENT = "#00BFAE"
    ACCENT_HOVER = "#00D4C1"
    ACCENT_PRESSED = "#009688"
    ACCENT_SOFT = "rgba(0, 191, 174, 0.12)"
    ACCENT_BORDER = "rgba(0, 191, 174, 0.25)"
    ACCENT_BORDER_STRONG = "rgba(0, 191, 174, 0.35)"

    # White button (primary action like Clone, Run Container)
    WHITE = "#FFFFFF"
    WHITE_HOVER = "#E8EAF0"
    WHITE_PRESSED = "#D3D6DE"

    # Semantic colors
    TEAL = "#00D4AA"
    ORANGE = "#FF9F1C"
    PURPLE = "#8B7CFF"
    BLUE = "#4C9AFF"
    GREEN = "#22C55E"
    RED = "#FF6B6B"
    YELLOW = "#FBBF24"
    AMBER = "#F59E0B"
    GOLD = "#FFC832"
    GREEN_BRIGHT = "#10B981"
    RED_STRONG = "#EF4444"
    BLUE_STRONG = "#3B82F6"
    PURPLE_BRIGHT = "#A855F7"
    NEON = "#00D6D5"

    # Translucent overlays (derived per theme: white on dark, black on light)
    OVERLAY_02 = "rgba(255, 255, 255, 0.02)"
    OVERLAY_03 = "rgba(255, 255, 255, 0.03)"
    OVERLAY_04 = "rgba(255, 255, 255, 0.04)"
    OVERLAY_05 = "rgba(255, 255, 255, 0.05)"
    OVERLAY_06 = "rgba(255, 255, 255, 0.06)"
    OVERLAY_07 = "rgba(255, 255, 255, 0.07)"
    OVERLAY_09 = "rgba(255, 255, 255, 0.09)"
    OVERLAY_12 = "rgba(255, 255, 255, 0.12)"
    OVERLAY_14 = "rgba(255, 255, 255, 0.14)"
    OVERLAY_15 = "rgba(255, 255, 255, 0.15)"
    OVERLAY_18 = "rgba(255, 255, 255, 0.18)"
    OVERLAY_22 = "rgba(255, 255, 255, 0.22)"
    OVERLAY_26 = "rgba(255, 255, 255, 0.26)"
    OVERLAY_28 = "rgba(255, 255, 255, 0.28)"
    OVERLAY_35 = "rgba(255, 255, 255, 0.35)"
    OVERLAY_90 = "rgba(255, 255, 255, 0.90)"
    OVERLAY_08 = "rgba(255, 255, 255, 0.08)"
    OVERLAY_10 = "rgba(255, 255, 255, 0.10)"
    OVERLAY_16 = "rgba(255, 255, 255, 0.16)"
    OVERLAY_20 = "rgba(255, 255, 255, 0.20)"
    OVERLAY_30 = "rgba(255, 255, 255, 0.30)"
    OVERLAY_40 = "rgba(255, 255, 255, 0.40)"
    OVERLAY_50 = "rgba(255, 255, 255, 0.50)"
    OVERLAY_55 = "rgba(255, 255, 255, 0.55)"

    # Translucent dark surfaces (floating panels, cards, dialogs)
    GLASS = "rgba(28, 30, 36, 0.85)"
    GLASS_2 = "rgba(34, 36, 42, 0.85)"
    GLASS_3 = "rgba(38, 40, 48, 0.90)"
    GLASS_DEEP = "rgba(24, 26, 32, 0.90)"
    GLASS_DARK = "rgba(18, 19, 22, 0.98)"
    GLASS_SOFT = "rgba(28, 30, 36, 0.55)"
    GLASS_FAINT = "rgba(20, 22, 26, 0.40)"
    GLASS_95 = "rgba(28, 30, 36, 0.95)"
    GLASS_2_95 = "rgba(34, 36, 42, 0.95)"
    GLASS_3_95 = "rgba(50, 52, 58, 0.95)"
    GLASS_DEEP_95 = "rgba(24, 26, 32, 0.95)"
    GLASS_2_90 = "rgba(34, 36, 42, 0.90)"
    GLASS_40_90 = "rgba(40, 42, 48, 0.90)"
    GLASS_50_90 = "rgba(50, 52, 58, 0.90)"
    GLASS_20_90 = "rgba(20, 22, 26, 0.90)"
    GLASS_12_75 = "rgba(12, 12, 14, 0.75)"
    GLASS_22_92 = "rgba(22, 23, 26, 0.92)"
    GLASS_22_59 = "rgba(22, 23, 26, 0.59)"
    GLASS_20_65 = "rgba(20, 21, 24, 0.65)"
    GLASS_16_71 = "rgba(16, 17, 20, 0.71)"
    GLASS_22_25_92 = "rgba(22, 25, 32, 0.92)"

    # Shadows / dark scrims
    SHADOW_25 = "rgba(0, 0, 0, 0.25)"
    SHADOW_35 = "rgba(0, 0, 0, 0.35)"
    SHADOW_40 = "rgba(0, 0, 0, 0.40)"
    SHADOW_55 = "rgba(0, 0, 0, 0.55)"
    SHADOW_60 = "rgba(0, 0, 0, 0.60)"
    SHADOW_78 = "rgba(0, 0, 0, 0.78)"

    # Accent alphas
    ACCENT_08 = "rgba(0, 191, 174, 0.08)"
    ACCENT_10 = "rgba(0, 191, 174, 0.10)"
    ACCENT_14 = "rgba(0, 191, 174, 0.14)"
    ACCENT_15 = "rgba(0, 191, 174, 0.15)"
    ACCENT_18 = "rgba(0, 191, 174, 0.18)"
    ACCENT_20 = "rgba(0, 191, 174, 0.20)"
    ACCENT_22 = "rgba(0, 191, 174, 0.22)"
    ACCENT_30 = "rgba(0, 191, 174, 0.30)"
    ACCENT_32 = "rgba(0, 191, 174, 0.32)"
    ACCENT_40 = "rgba(0, 191, 174, 0.40)"
    ACCENT_60 = "rgba(0, 191, 174, 0.60)"
    ACCENT_70 = "rgba(0, 191, 174, 0.70)"
    ACCENT_72 = "rgba(0, 191, 174, 0.72)"
    ACCENT_85 = "rgba(0, 191, 174, 0.85)"
    ACCENT_90 = "rgba(0, 191, 174, 0.90)"

    # Semantic translucent variants
    RED_SOFT = "rgba(255, 107, 107, 0.10)"
    RED_12 = "rgba(255, 107, 107, 0.12)"
    RED_18 = "rgba(255, 107, 107, 0.18)"
    RED_BORDER = "rgba(255, 107, 107, 0.20)"
    RED_30 = "rgba(255, 107, 107, 0.30)"
    RED_40 = "rgba(255, 107, 107, 0.40)"
    RED_50 = "rgba(255, 107, 107, 0.50)"
    RED_STRONG_SOFT = "rgba(255, 80, 80, 0.15)"
    RED_STRONG_BORDER = "rgba(255, 80, 80, 0.30)"
    RED_STRONG_25 = "rgba(255, 80, 80, 0.25)"
    RED_STRONG_45 = "rgba(255, 80, 80, 0.45)"
    RED_STRONG_60 = "rgba(255, 80, 80, 0.60)"
    RED_STRONG_80 = "rgba(255, 80, 80, 0.80)"
    ORANGE_07 = "rgba(255, 159, 28, 0.07)"
    ORANGE_SOFT = "rgba(255, 159, 28, 0.12)"
    ORANGE_14 = "rgba(255, 159, 28, 0.14)"
    ORANGE_25 = "rgba(255, 159, 28, 0.25)"
    BLUE_SOFT = "rgba(76, 154, 255, 0.12)"
    BLUE_STRONG_SOFT = "rgba(59, 130, 246, 0.10)"
    BLUE_STRONG_BORDER = "rgba(59, 130, 246, 0.20)"
    BLUE_STRONG_30 = "rgba(59, 130, 246, 0.30)"
    BLUE_STRONG_40 = "rgba(59, 130, 246, 0.40)"
    PURPLE_SOFT = "rgba(168, 85, 247, 0.15)"
    PURPLE_BORDER = "rgba(168, 85, 247, 0.25)"
    PURPLE_30 = "rgba(168, 85, 247, 0.30)"
    PURPLE_35 = "rgba(168, 85, 247, 0.35)"
    PURPLE_SOFT_12 = "rgba(139, 124, 255, 0.12)"
    GREEN_SOFT = "rgba(16, 185, 129, 0.08)"
    GREEN_BORDER = "rgba(16, 185, 129, 0.12)"
    AUR_SOFT = "rgba(255, 138, 101, 0.12)"
    LOCAL_SOFT = "rgba(163, 166, 176, 0.12)"
    TEXT_3_SOFT = "rgba(92, 94, 102, 0.12)"
    GOLD_SOFT = "rgba(255, 200, 50, 0.12)"
    GOLD_BORDER = "rgba(255, 200, 50, 0.35)"
    NEON_18 = "rgba(0, 214, 213, 0.18)"
    NEON_35 = "rgba(0, 214, 213, 0.35)"
    NEON_45 = "rgba(0, 214, 213, 0.45)"
    NEON_60 = "rgba(0, 214, 213, 0.60)"
    NEON_85 = "rgba(0, 214, 213, 0.85)"
    TRAFFIC_RED = "#FF5F57"
    TRAFFIC_RED_TEXT = "rgba(80, 20, 20, 0.70)"
    TRAFFIC_YELLOW_TEXT = "rgba(120, 80, 10, 0.70)"
    TRAFFIC_GREEN_TEXT = "rgba(10, 70, 20, 0.70)"
    TRAFFIC_YELLOW = "#FEBC2E"
    TRAFFIC_GREEN = "#29C840"

    # Source colors (canonical — ONE palette for all sources)
    SRC_PACMAN = "#4FC3F7"
    SRC_AUR = "#FF8A65"
    SRC_FLATPAK = "#26A69A"
    SRC_NPM = "#E53935"
    SRC_LOCAL = "#A3A6B0"
    SRC_FIRMWARE = "#A3A6B0"
    SRC_DOCKER = "#2496ED"
    SRC_BREW = "#8B5CF6"
    SRC_PIPX = "#00ACC1"

    # Toast
    TOAST_INFO = "#4C9AFF"
    TOAST_SUCCESS = "#22C55E"
    TOAST_WARNING = "#FF9F1C"
    TOAST_ERROR = "#FF6B6B"


# ── Source color map ───────────────────────────────────────────────

SourceColors = {
    "pacman": Colors.SRC_PACMAN,
    "AUR": Colors.SRC_AUR,
    "Flatpak": Colors.SRC_FLATPAK,
    "npm": Colors.SRC_NPM,
    "Firmware": Colors.SRC_FIRMWARE,
    "Docker": Colors.SRC_DOCKER,
    "Brew": Colors.SRC_BREW,
    "pipx": Colors.SRC_PIPX,
}


# ── Typography ─────────────────────────────────────────────────────

class Fonts:
    """Font families, sizes, and weights."""

    FAMILY = ("'Segoe UI', 'Noto Sans', 'Noto Sans Sinhala', 'Noto Sans Devanagari',"
              " 'Noto Sans Tamil', 'Noto Sans Telugu', 'Noto Sans Bengali',"
              " 'Noto Sans Gujarati', 'Noto Sans Marathi', 'Noto Sans Kannada',"
              " 'Noto Sans Malayalam', 'Noto Sans Gurmukhi', 'Noto Sans Oriya',"
              " 'Noto Sans Arabic', 'Noto Sans Hebrew', 'Noto Sans Thai',"
              " 'Noto Sans Georgian', 'Noto Sans Armenian', -apple-system, sans-serif")
    MONO = "'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace"
    DEFAULT_FAMILY = FAMILY
    DEFAULT_MONO = MONO

    # Size scale (px)
    MICRO = "8px"
    TINY = "9px"
    XS = "10px"
    SM = "11px"
    MD = "12px"
    BASE = "13px"
    LG = "14px"
    CARD_TITLE = "15px"
    XL = "16px"
    XXL = "18px"
    HERO = "20px"
    DISPLAY = "24px"
    PAGE_TITLE = "28px"

    # Weights
    REGULAR = "400"
    MEDIUM = "500"
    SEMI = "600"
    BOLD = "700"


FONT_SIZE_NAMES = (
    "MICRO", "TINY", "XS", "SM", "MD", "BASE", "LG", "CARD_TITLE",
    "XL", "XXL", "HERO", "DISPLAY", "PAGE_TITLE",
)
DEFAULT_FONT_SIZES = {
    name: getattr(Fonts, name) for name in FONT_SIZE_NAMES
}


# ── Border radius ──────────────────────────────────────────────────

class Radii:
    """Border radius scale (px)."""

    NONE = "0"
    SM = "4"
    CHECKBOX = "5"
    MD = "8"
    LG = "12"
    XL = "14"
    FULL = "9999"


# ── Spacing ────────────────────────────────────────────────────────

class Spacing:
    """Spacing scale (px)."""

    XS = "4"
    SM = "8"
    MD = "12"
    LG = "16"
    XL = "20"
    XXL = "24"
    XXXL = "32"


# ── Scrollbars ─────────────────────────────────────────────────────

class Scrollbar:
    """Scrollbar metrics (px)."""

    WIDTH = "8"
    RADIUS = "4"
    MARGIN = "2"
    MIN_LEN = "24"


RADII_NAMES = ("SM", "CHECKBOX", "MD", "LG", "XL")
DEFAULT_RADII = {name: getattr(Radii, name) for name in RADII_NAMES}
SPACING_NAMES = ("XS", "SM", "MD", "LG", "XL", "XXL", "XXXL")
DEFAULT_SPACING = {name: getattr(Spacing, name) for name in SPACING_NAMES}
DEFAULT_SCROLLBAR = {
    name: getattr(Scrollbar, name)
    for name in ("WIDTH", "RADIUS", "MARGIN", "MIN_LEN")
}


# ── Shared QSS blocks for settings views ───────────────────────────

_CHECK_ICON = _icon_path("ui/check")


def _build_qss():
    """Generate QSS blocks from current Colors/Fonts/Radii values."""
    return {
        # NOTE: scoped to the card frame itself. An unscoped declaration
        # block leaks border/background onto EVERY child widget (labels,
        # checkboxes...) via Qt stylesheet inheritance.
        "CARD": f"""
            QFrame#settingsCard {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radii.XL}px;
            }}
        """,
        "CHECKBOX": f"""
            QCheckBox {{
                color: {Colors.TEXT};
                font-size: {Fonts.BASE};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 1px solid {Colors.BORDER_INPUT};
                background-color: {Colors.INPUT_BG};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.ACCENT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.ACCENT};
                border: 1px solid {Colors.ACCENT};
                image: url("{_CHECK_ICON}");
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: {Colors.ACCENT_HOVER};
                border-color: {Colors.ACCENT_HOVER};
            }}
            QCheckBox::indicator:disabled {{
                border-color: {Colors.BORDER_INPUT};
                background-color: transparent;
            }}
        """,
        "COMBO": f"""
            QComboBox {{
                background-color: {Colors.INPUT_BG};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {Radii.MD}px;
                color: {Colors.TEXT};
                font-size: {Fonts.BASE};
                padding: 6px 12px;
            }}
            QComboBox:hover {{
                border-color: {Colors.BORDER_HOVER};
            }}
            QComboBox:focus {{
                border: 1px solid {Colors.ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {Colors.TEXT_2};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.SURFACE_2};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radii.MD}px;
                color: {Colors.TEXT};
                selection-background-color: {Colors.ACCENT_SOFT};
                padding: 4px;
            }}
        """,
        "SPINBOX": f"""
            QSpinBox {{
                background-color: {Colors.INPUT_BG};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {Radii.MD}px;
                color: {Colors.TEXT};
                font-size: {Fonts.BASE};
                padding: 6px 8px;
            }}
            QSpinBox:hover {{
                border-color: {Colors.BORDER_HOVER};
            }}
            QSpinBox:focus {{
                border: 1px solid {Colors.ACCENT};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: transparent;
                border: none;
                width: 16px;
            }}
            QSpinBox::up-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid {Colors.TEXT_2};
            }}
            QSpinBox::down-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {Colors.TEXT_2};
            }}
        """,
        "LINEEDIT": f"""
            QLineEdit {{
                background-color: {Colors.INPUT_BG};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {Radii.MD}px;
                color: {Colors.TEXT};
                font-size: {Fonts.BASE};
                padding: 6px 12px;
            }}
            QLineEdit:hover {{
                border-color: {Colors.BORDER_HOVER};
            }}
            QLineEdit:focus {{
                border: 1px solid {Colors.ACCENT};
            }}
        """,
        "BTN_OUTLINE": f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.ACCENT};
                border: 1px solid {Colors.ACCENT_BORDER_STRONG};
                border-radius: {Radii.MD}px;
                padding: 8px 16px;
                font-size: {Fonts.BASE};
                font-weight: {Fonts.MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_SOFT};
                border-color: {Colors.ACCENT};
            }}
        """,
        "BTN_GHOST": f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_2};
                border: 1px solid {Colors.BORDER_HOVER};
                border-radius: {Radii.MD}px;
                padding: 8px 16px;
                font-size: {Fonts.BASE};
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
                border-color: {Colors.BORDER_STRONG};
                color: {Colors.TEXT};
            }}
        """,
        "HINT": f"color: {Colors.TEXT_2}; font-size: {Fonts.MD}; border: none;",
        "SCROLL_AREA": (
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 6px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.08);"
            "  border-radius: 3px; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.14); }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"),
    }


class _QSS:
    """Dynamic QSS blocks — call regenerate() after changing tokens."""

    def regenerate(self):
        for k, v in _build_qss().items():
            setattr(self, k, v)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        self.regenerate()
        return object.__getattribute__(self, name)


QSS = _QSS()
QSS.regenerate()


# ── Main window stylesheet (rebuilt on theme change) ───────────────

# Window frame effects — runtime-overridden from user settings by
# the main window's apply_window_effects(). Glow border is OFF by
# default because translucent rims can leave artifacts on some
# compositors/GPU drivers.
WINDOW_GLOW = False
WINDOW_RADIUS = 8
WINDOW_OPACITY = 0.75


def _build_main_stylesheet():
    frame_border = (
        f"border: 1px solid {Colors.ACCENT_SOFT};" if WINDOW_GLOW
        else "border: none;")
    bg = qcolor(Colors.BG)
    window_bg = (
        f"rgba({bg.red()}, {bg.green()}, {bg.blue()}, {WINDOW_OPACITY})"
    )
    return f"""
QMainWindow {{
    background-color: transparent;
    color: {Colors.TEXT};
}}

QWidget#appOuter {{
    background-color: transparent;
}}

QFrame#appWindow {{
    background-color: {window_bg};
    {frame_border}
    border-radius: {WINDOW_RADIUS}px;
}}

QWidget#appTitleBar {{
    background-color: transparent;
    border-bottom: 1px solid {Colors.BORDER};
    border-top-left-radius: {WINDOW_RADIUS}px;
    border-top-right-radius: {WINDOW_RADIUS}px;
}}

QLabel#titleBarLabel {{
    color: {Colors.TEXT_2};
    font-size: {Fonts.BASE};
    font-weight: 500;
}}

QPushButton#titleBarCloseBtn,
QPushButton#titleBarMinBtn,
QPushButton#titleBarMaxBtn {{
    border: none;
    border-radius: 7px;
    font-size: {Fonts.SM};
    font-weight: 700;
    padding: 0;
}}

QPushButton#titleBarCloseBtn {{
    background-color: {Colors.TRAFFIC_RED};
    color: transparent;
}}
QPushButton#titleBarCloseBtn:hover {{
    background-color: {Colors.TRAFFIC_RED};
    color: {Colors.TRAFFIC_RED_TEXT};
}}

QPushButton#titleBarMinBtn {{
    background-color: {Colors.TRAFFIC_YELLOW};
    color: transparent;
}}
QPushButton#titleBarMinBtn:hover {{
    background-color: {Colors.TRAFFIC_YELLOW};
    color: {Colors.TRAFFIC_YELLOW_TEXT};
}}

QPushButton#titleBarMaxBtn {{
    background-color: {Colors.TRAFFIC_GREEN};
    color: transparent;
}}
QPushButton#titleBarMaxBtn:hover {{
    background-color: {Colors.TRAFFIC_GREEN};
    color: {Colors.TRAFFIC_GREEN_TEXT};
}}

QWidget#appBody {{
    background-color: transparent;
}}

QWidget {{
    background-color: transparent;
    color: {Colors.TEXT};
    font-family: {Fonts.FAMILY};
    font-size: {Fonts.BASE};
}}

QLineEdit {{
    background-color: {Colors.INPUT_BG};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    padding: 8px 16px;
    font-size: {Fonts.LG};
    selection-background-color: {Colors.ACCENT};
}}

QLineEdit:focus {{
    background-color: {Colors.INPUT_BG_FOCUS};
    border: 1px solid {Colors.BORDER_FOCUS};
}}

QPushButton {{
    background-color: {Colors.CARD};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 8px 18px;
    font-weight: 500;
    font-size: {Fonts.BASE};
}}

QPushButton:hover {{
    background-color: {Colors.CARD_HOVER};
    border-color: {Colors.BORDER_HOVER};
}}

QPushButton:pressed {{
    background-color: {Colors.SURFACE_3};
}}

QPushButton#loadMoreBtn {{
    background-color: {Colors.CARD};
    color: {Colors.TEXT};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 10px 18px;
    font-size: {Fonts.BASE};
    font-weight: 500;
}}

QPushButton#loadMoreBtn:hover {{
    background-color: {Colors.CARD_HOVER};
    border-color: {Colors.ACCENT};
    color: {Colors.TEXT};
}}

QPushButton#loadMoreBtn:pressed {{
    background-color: {Colors.SURFACE_3};
}}

QWidget#sidebar {{
    background-color: {Colors.SIDEBAR};
    border-right: 1px solid {Colors.BORDER};
}}

QPushButton#sidebarBtn {{
    background-color: transparent;
    border: none;
    color: {Colors.TEXT_2};
    padding: 0;
    text-align: center;
    font-size: {Fonts.BASE};
    font-weight: 500;
    border-radius: 8px;
}}

QPushButton#sidebarBtn:hover {{
    background-color: {Colors.BORDER};
    color: {Colors.TEXT};
}}

QPushButton#sidebarBtn:checked {{
    background-color: {Colors.ACCENT_SOFT};
    color: {Colors.TEXT};
}}

QWidget#sidebarNavIcon {{
    background-color: transparent;
    font-size: {Fonts.DISPLAY};
    color: {Colors.TEXT_2};
}}

QLabel#sidebarLabel {{
    color: {Colors.TEXT_2};
    font-size: {Fonts.SM};
    font-weight: 500;
    letter-spacing: 0.3px;
}}

QPushButton#sidebarBtn:hover QWidget#sidebarNavIcon {{
    color: {Colors.TEXT};
}}

QPushButton#sidebarBtn:checked QWidget#sidebarNavIcon {{
    color: {Colors.ACCENT};
}}

QLabel#sidebarSection {{
    color: {Colors.TEXT_3};
    font-size: {Fonts.TINY};
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 0;
    max-height: 0;
}}

QLabel#sidebarLogo {{
    font-size: {Fonts.HERO};
}}

QLabel#navBadge {{
    color: {Colors.ACCENT};
    background: transparent;
    font-size: {Fonts.SM};
    font-weight: 700;
}}

QFrame#appHeader {{
    background-color: {Colors.SIDEBAR};
    border-bottom: 1px solid {Colors.BORDER};
}}

QLabel#headerLabel {{
    color: {Colors.TEXT};
    font-size: {Fonts.XXL};
    font-weight: 600;
}}

QLabel#headerInfo {{
    color: {Colors.TEXT_2};
    font-size: {Fonts.MD};
}}

QTableWidget {{
    background-color: {Colors.INPUT_BG};
    alternate-background-color: {Colors.SURFACE};
    gridline-color: {Colors.BORDER};
    border: 1px solid {Colors.BORDER};
    border-radius: 14px;
    selection-background-color: {Colors.ACCENT_SOFT};
    selection-color: {Colors.TEXT};
}}

QTableWidget::item {{
    padding: 12px 10px;
    border: none;
    border-bottom: 1px solid {Colors.BORDER};
}}

QTableWidget::item:hover {{
    background-color: {Colors.BORDER};
    border-bottom: 1px solid {Colors.ACCENT_SOFT};
}}

QTableWidget::item:selected {{
    background-color: {Colors.ACCENT_SOFT};
    color: {Colors.TEXT};
}}

QTableView#updatesTable {{
    background-color: {Colors.SIDEBAR};
    border: 1px solid {Colors.BORDER};
    border-radius: 14px;
}}

QHeaderView::section {{
    background-color: {Colors.SIDEBAR};
    color: {Colors.TEXT_2};
    padding: 10px 10px;
    border: none;
    font-weight: 600;
    font-size: {Fonts.SM};
    text-transform: uppercase;
    letter-spacing: 0.4px;
    border-bottom: 1px solid {Colors.BORDER};
}}

QTextEdit {{
    background-color: {Colors.SIDEBAR};
    color: {Colors.TEXT_2};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    font-family: {Fonts.MONO};
    font-size: {Fonts.MD};
    padding: 10px;
}}

QLabel {{
    color: {Colors.TEXT};
}}

QLabel#sectionLabel {{
    color: {Colors.TEXT_2};
    font-size: {Fonts.XS};
    font-weight: 500;
    background: transparent;
    border: none;
}}

QFrame {{
    background-color: transparent;
    border: none;
}}

QCheckBox {{
    color: {Colors.TEXT};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid {Colors.TEXT_3};
    background-color: {Colors.INPUT_BG};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.ACCENT};
    border: 1.5px solid {Colors.ACCENT};
}}

QCheckBox::indicator:hover {{
    border-color: {Colors.ACCENT};
}}

QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QListWidget::item:hover {{
    background-color: {Colors.ACCENT_SOFT};
    border-radius: 8px;
}}

QListWidget::item:selected {{
    background-color: {Colors.ACCENT};
    color: {Colors.TEXT_ON_ACCENT};
    border-radius: 8px;
}}

QWidget#sourceChip {{
    background-color: {Colors.ACCENT_SOFT};
    border: 1px solid {Colors.ACCENT_BORDER};
    border-radius: 6px;
}}

QWidget#sourceChip QLabel {{
    color: {Colors.ACCENT};
    font-size: {Fonts.SM};
    padding: 0 4px;
}}

QProgressBar {{
    border: none;
    border-radius: 4px;
    text-align: center;
    background-color: {Colors.INPUT_BG};
}}

QProgressBar::chunk {{
    background-color: {Colors.ACCENT};
    border-radius: 4px;
}}

QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: {Scrollbar.WIDTH}px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {Colors.TEXT_3};
    border-radius: {Scrollbar.RADIUS}px;
    min-height: {Scrollbar.MIN_LEN}px;
    margin: {Scrollbar.MARGIN}px;
}}

QScrollBar::handle:vertical:hover {{
    background: {Colors.TEXT_2};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: transparent;
    height: 0;
}}

QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
    border: none;
    width: 0;
    height: 0;
    background: transparent;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: {Scrollbar.WIDTH}px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {Colors.TEXT_3};
    border-radius: {Scrollbar.RADIUS}px;
    min-width: {Scrollbar.MIN_LEN}px;
    margin: {Scrollbar.MARGIN}px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {Colors.TEXT_2};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: transparent;
    width: 0;
}}

QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
    border: none;
    width: 0;
    height: 0;
    background: transparent;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

QScrollArea::corner {{
    background: transparent;
    border: none;
}}
"""


DARK_STYLESHEET = _build_main_stylesheet()


def rebuild_stylesheet():
    """Rebuild DARK_STYLESHEET after a theme change."""
    global DARK_STYLESHEET
    DARK_STYLESHEET = _build_main_stylesheet()


# ── Convenience alias ──────────────────────────────────────────────

class T:
    """Shorthand access to all tokens: T.c, T.f, T.r, T.s"""

    c = Colors
    f = Fonts
    r = Radii
    s = Spacing
    src = SourceColors
