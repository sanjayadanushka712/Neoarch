"""Application styles and design system.

THE single place to change reusable styles and fonts for every page.

Every builder below reads the live token values from ``tokens`` (Colors,
Fonts, Radii, Spacing), so restyling the whole app means editing one of two
files:

  * ``tokens.py``  – the token *values* (colors, font families/sizes/weights,
                     radii, spacing),
  * ``styles.py``  – the reusable *patterns* built from those values.

Pages must never paste their own copy of a primitive (menus, scrollbars,
inputs, buttons, labels, cards, chips…) — import a builder here instead so
all pages stay in sync.

Example
-------
    from neoarch.frontend.styles import Styles

    menu.setStyleSheet(Styles.menu())
    lbl.setStyleSheet(Styles.text(Styles.TEXT_2, Fonts.SM, Fonts.MEDIUM))
    card.setStyleSheet(Styles.card())
"""

__all__ = ["Styles", "DARK_STYLESHEET"]

from neoarch.frontend.icon_registry import icon_path as _icon_path
from neoarch.frontend.tokens import (
    Colors, Fonts, Radii, DARK_STYLESHEET,
)


_CHECK_ICON = _icon_path("ui/check")


_COLOR_ALIASES = {name for name in vars(Colors) if name.isupper()}


class _StylesMeta(type):
    """Resolve ``Styles.TEXT`` etc. against the live ``Colors`` values."""

    def __getattr__(cls, name):
        if name in _COLOR_ALIASES:
            return getattr(Colors, name)
        raise AttributeError(f"type object 'Styles' has no attribute {name!r}")


class Styles(metaclass=_StylesMeta):
    """Reusable style builders — the single place to restyle the app.

    All builders return QSS strings assembled from the live token values at
    call time, so theme changes (``themes.ThemeManager``) are picked up
    automatically.
    """

    # ── Typography helpers ──────────────────────────────────────────

    @staticmethod
    def text(color=None, size=Fonts.BASE, weight=Fonts.REGULAR,
             mono=False):
        """QSS for a plain label."""
        color = color or Colors.TEXT
        css = f"color: {color}; font-size: {size}; font-weight: {weight};"
        if mono:
            css += f" font-family: {Fonts.MONO};"
        return css

    @staticmethod
    def font(family=None, size=Fonts.BASE, weight=None, color=None):
        """QSS font declaration fragment (no selector)."""
        family = family or Fonts.FAMILY
        css = f"font-family: {family}; font-size: {size};"
        if weight:
            css += f" font-weight: {weight};"
        if color:
            css += f" color: {color};"
        return css

    @staticmethod
    def overline(color=None, size=Fonts.XS, weight=Fonts.SEMI):
        """Uppercase section/sidebar labels — QSS only (use QFont for Qt)."""
        color = color or Colors.TEXT_2
        return (f"color: {color}; font-size: {size}; font-weight: {weight};"
                " text-transform: uppercase; letter-spacing: 0.8px;")

    # ── Surfaces / cards ────────────────────────────────────────────

    @staticmethod
    def card(bg=None, border=None, radius=Radii.XL, hover=None):
        """Surface card frame (scoped to a named widget to avoid leaking
        onto children via Qt stylesheet inheritance)."""
        bg = bg or Colors.SURFACE
        border = border or Colors.BORDER
        if hover:
            return f"""
                QFrame#cardFrame {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: {radius}px;
                }}
                QFrame#cardFrame:hover {{ background-color: {hover}; }}
            """
        return f"""
            QFrame#cardFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {radius}px;
            }}
        """

    @staticmethod
    def panel(bg="transparent", border="none", radius=Radii.NONE):
        """Generic widget surface — set objectName('panelWidget') to scope."""
        return f"""
            QWidget#panelWidget {{
                background-color: {bg};
                border: {border};
                border-radius: {radius}px;
            }}
        """

    @staticmethod
    def hairline():  # vertical / horizontal divider
        return f"background: {Colors.BORDER}; border: none;"

    # ── Inputs ──────────────────────────────────────────────────────

    @staticmethod
    def input(padding="6px 12px", size=Fonts.BASE, radius=Radii.MD,
              selection=None):
        """QLineEdit."""
        sel = selection or Colors.ACCENT
        return f"""
            QLineEdit {{
                background-color: {Colors.INPUT_BG};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
                selection-background-color: {sel};
            }}
            QLineEdit:hover {{ border-color: {Colors.BORDER_HOVER}; }}
            QLineEdit:focus {{ border: 1px solid {Colors.ACCENT}; }}
            QLineEdit::placeholder {{ color: {Colors.TEXT_3}; }}
        """

    @staticmethod
    def combo(padding="6px 10px", size=Fonts.BASE, radius=Radii.MD):
        """QComboBox (incl. popup view)."""
        return f"""
            QComboBox {{
                background-color: {Colors.INPUT_BG};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
                min-width: 100px;
            }}
            QComboBox:hover {{ border-color: {Colors.BORDER_HOVER}; }}
            QComboBox:focus {{ border: 1px solid {Colors.ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {Colors.TEXT_2};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.SURFACE_2};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: {radius}px;
                selection-background-color: {Colors.ACCENT_SOFT};
                selection-color: {Colors.TEXT};
                outline: none;
                padding: 4px;
            }}
        """

    @staticmethod
    def spinbox(padding="6px 8px", size=Fonts.BASE, radius=Radii.MD):
        """QSpinBox."""
        return f"""
            QSpinBox {{
                background-color: {Colors.INPUT_BG};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
            }}
            QSpinBox:hover {{ border-color: {Colors.BORDER_HOVER}; }}
            QSpinBox:focus {{ border: 1px solid {Colors.ACCENT}; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: transparent; border: none; width: 16px;
            }}
        """

    @staticmethod
    def checkbox(size=18, radius=6, spacing=8, label_size=Fonts.BASE):
        """QCheckBox with an SVG check mark on checked state."""
        return f"""
            QCheckBox {{
                color: {Colors.TEXT};
                font-size: {label_size};
                spacing: {spacing}px;
            }}
            QCheckBox::indicator {{
                width: {size}px;
                height: {size}px;
                border-radius: {radius}px;
                border: 1px solid {Colors.BORDER_INPUT};
                background-color: {Colors.INPUT_BG};
            }}
            QCheckBox::indicator:hover {{ border-color: {Colors.ACCENT}; }}
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
        """

    @staticmethod
    def plain_edit(padding="6px 8px", size=Fonts.MD, radius=Radii.MD,
                   mono=True):
        """QPlainTextEdit / QTextEdit (mono by default)."""
        family = Fonts.MONO if mono else Fonts.FAMILY
        return f"""
            QPlainTextEdit, QTextEdit {{
                background-color: {Colors.INPUT_BG};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER_INPUT};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
                font-family: {family};
                selection-background-color: {Colors.ACCENT};
            }}
            QPlainTextEdit:hover, QTextEdit:hover {{
                border-color: {Colors.BORDER_HOVER};
            }}
            QPlainTextEdit:focus, QTextEdit:focus {{
                border: 1px solid {Colors.ACCENT};
            }}
        """

    # ── Menus & popups ──────────────────────────────────────────────

    @staticmethod
    def menu(bg=None, fg=None, size=Fonts.MD,
             radius=Radii.MD, selected=None, border=None):
        """QMenu block."""
        bg = bg or Colors.SURFACE_3
        fg = fg or Colors.TEXT
        selected = selected or Colors.ACCENT_SOFT
        border = border or Colors.BORDER_STRONG
        return f"""
            QMenu {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: {radius}px;
                padding: 4px;
            }}
            QMenu::item {{ padding: 5px 20px; border-radius: 4px; font-size: {size}; }}
            QMenu::item:selected {{ background-color: {selected}; color: {Colors.TEXT}; }}
        """

    @staticmethod
    def scrollbar(width=6, color=None, hover=None, min_len=30):
        """Transparent QScrollArea + slim vertical scrollbar (the common
        pattern used across all full-page views)."""
        color = color or Colors.BORDER_INPUT
        hover = hover or Colors.OVERLAY_14
        radius = max(2, int(width) // 2)
        return (
            "QScrollArea { background: transparent; border: none; }"
            f"QScrollBar:vertical {{ background: transparent; width: {width}px; }}"
            f"QScrollBar::handle:vertical {{ background: {color};"
            f" border-radius: {radius}px; min-height: {min_len}px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: {hover}; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical"
            " { height: 0; }")

    # ── Buttons ─────────────────────────────────────────────────────

    @staticmethod
    def btn_outline(padding="8px 16px", size=Fonts.BASE, radius=Radii.MD):
        """Transparent accent-outlined button."""
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.ACCENT};
                border: 1px solid {Colors.ACCENT_BORDER_STRONG};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
                font-weight: {Fonts.MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {Colors.ACCENT_SOFT};
                border-color: {Colors.ACCENT};
            }}
        """

    @staticmethod
    def btn_ghost(padding="8px 16px", size=Fonts.BASE, radius=Radii.MD):
        """Subtle bordered neutral button."""
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_2};
                border: 1px solid {Colors.BORDER_HOVER};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
                border-color: {Colors.BORDER_STRONG};
                color: {Colors.TEXT};
            }}
        """

    @staticmethod
    def btn_primary(padding="8px 18px", size=Fonts.BASE, radius=Radii.MD):
        """Solid accent (primary action) button."""
        return f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: {Colors.TEXT_ON_ACCENT};
                border: 1px solid {Colors.ACCENT};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
                font-weight: {Fonts.SEMI};
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {Colors.ACCENT_PRESSED}; }}
        """

    @staticmethod
    def btn_white(padding="7px 18px", size=Fonts.MD, radius=Radii.MD,
                  weight=Fonts.SEMI):
        """White 'hero' button (Clone, Run Container…)."""
        return f"""
            QPushButton {{
                background-color: {Colors.WHITE};
                color: {Colors.TEXT_ON_WHITE};
                border: 1px solid {Colors.OVERLAY_90};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
                font-weight: {weight};
            }}
            QPushButton:hover {{ background-color: {Colors.WHITE_HOVER}; }}
            QPushButton:pressed {{ background-color: {Colors.WHITE_PRESSED}; }}
        """

    @staticmethod
    def btn_white_disabled():
        """Append to btn_white: disabled state rules."""
        return f"""
            QPushButton:disabled {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_3};
                border-color: {Colors.BORDER_INPUT};
            }}
        """

    @staticmethod
    def btn_secondary(padding="7px 18px", size=Fonts.MD, radius=Radii.MD):
        """Transparent bordered neutral (dialog secondary)."""
        return f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_2};
                border: 1px solid {Colors.BORDER};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
                font-weight: {Fonts.MEDIUM};
            }}
            QPushButton:hover {{
                background: {Colors.BORDER};
                color: {Colors.TEXT};
            }}
        """

    @staticmethod
    def btn_danger(padding="7px 18px", size=Fonts.MD, radius=Radii.MD):
        """Destructive action button."""
        return f"""
            QPushButton {{
                background-color: {Colors.RED_STRONG_SOFT};
                color: {Colors.RED};
                border: 1px solid {Colors.RED_STRONG_BORDER};
                border-radius: {radius}px;
                padding: {padding};
                font-size: {size};
                font-weight: {Fonts.SEMI};
            }}
            QPushButton:hover {{
                background-color: {Colors.RED_STRONG_25};
                border-color: {Colors.RED_STRONG_45};
            }}
        """

    @staticmethod
    def btn_danger_outline(padding="0 14px", size=Fonts.SM, radius=Radii.MD):
        """Compact red-outline button (danger, non-filled)."""
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.RED};
                border: 1px solid {Colors.RED_STRONG_BORDER};
                border-radius: {radius}px;
                font-weight: {Fonts.BOLD};
                font-size: {size};
                padding: {padding};
            }}
            QPushButton:hover {{
                background-color: {Colors.RED_12};
                border-color: {Colors.RED_STRONG_60};
            }}
            QPushButton:pressed {{
                background-color: {Colors.RED_BORDER};
                border-color: {Colors.RED_STRONG_80};
            }}
        """

    @staticmethod
    def btn_disabled(color=None, border=None):
        """Append to any button QSS: disabled state rules."""
        color = color or Colors.OVERLAY_35
        border = border or Colors.BORDER_INPUT
        return f"""
            QPushButton:disabled {{
                color: {color};
                border-color: {border};
                background-color: transparent;
            }}
        """

    @staticmethod
    def btn_card(padding="8px 18px", size=Fonts.BASE, radius=Radii.LG):
        """Default card-surface button (main-window base QPushButton)."""
        return f"""
            QPushButton {{
                background-color: {Colors.CARD};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: {radius}px;
                padding: {padding};
                font-weight: {Fonts.MEDIUM};
                font-size: {size};
            }}
            QPushButton:hover {{
                background-color: {Colors.CARD_HOVER};
                border-color: {Colors.BORDER_HOVER};
            }}
            QPushButton:pressed {{ background-color: {Colors.SURFACE_3}; }}
        """

    # ── Chips / badges ──────────────────────────────────────────────

    @staticmethod
    def chip(bg=None, fg=None, border=None,
             radius=Radii.SM, size=Fonts.SM):
        """Small pill/badge (source chips, status tags)."""
        bg = bg or Colors.ACCENT_SOFT
        fg = fg or Colors.ACCENT
        border = border or Colors.ACCENT_BORDER
        return f"""
            QWidget#styledChip {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {radius}px;
            }}
            QWidget#styledChip QLabel {{
                color: {fg};
                font-size: {size};
                padding: 0 4px;
            }}
        """

    @staticmethod
    def source_chip(size=Fonts.SM):
        """The canonical source badge (accent pill)."""
        return Styles.chip(bg=Colors.ACCENT_SOFT, fg=Colors.ACCENT,
                           border=Colors.ACCENT_BORDER, radius=Radii.SM,
                           size=size)

    # ── Backwards-compatible app stylesheet accessor ────────────────

    @staticmethod
    def get_dark_stylesheet():
        """The app-wide main-window stylesheet (rebuilt on theme change)."""
        from neoarch.frontend import tokens
        return tokens.DARK_STYLESHEET