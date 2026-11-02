import json
import re

import pytest

from neoarch.frontend import themes
from neoarch.frontend.themes import (
    BUILTIN_THEME_DIR,
    SYSTEM_THEME_ID,
    THEMES,
    ThemeManager,
    get_theme_data,
    load_themes,
)


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _write_theme(directory, filename, data):
    path = directory / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_builtin_themes_load():
    themes = load_themes([BUILTIN_THEME_DIR])

    assert set(themes) == {"dark", "light", "dracula", "nord"}
    assert themes["dark"]["colors"]["BG"] == "#0C0C0E"
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", themes["light"]["colors"]["BG"])
    assert themes["light"]["is_dark"] is False


def test_partial_user_theme_inherits_dark(tmp_path):
    _write_theme(tmp_path, "custom.json", {
        "id": "custom",
        "name": "Custom",
        "colors": {"ACCENT": "#123456"},
    })

    themes = load_themes([BUILTIN_THEME_DIR, tmp_path])

    assert themes["custom"]["name"] == "Custom"
    assert themes["custom"]["colors"]["ACCENT"] == "#123456"
    assert themes["custom"]["colors"]["BG"] == themes["dark"]["colors"]["BG"]
    assert themes["custom"]["source_colors"] == themes["dark"]["source_colors"]


def test_later_directories_override_earlier_ones(tmp_path):
    _write_theme(tmp_path, "light.json", {
        "id": "light",
        "name": "Light Override",
        "colors": {"BG": "#FFFFFF"},
    })

    themes = load_themes([BUILTIN_THEME_DIR, tmp_path])

    assert themes["light"]["name"] == "Light Override"
    assert themes["light"]["colors"]["BG"] == "#FFFFFF"


def test_invalid_theme_files_are_skipped(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    _write_theme(tmp_path, "bad-colors.json", {
        "id": "bad",
        "colors": ["not", "a", "dict"],
    })

    themes = load_themes([BUILTIN_THEME_DIR, tmp_path])

    assert "broken" not in themes
    assert "bad" not in themes


def test_system_theme_follows_os_and_persists_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    try:
        assert manager.apply_theme(SYSTEM_THEME_ID)
        assert manager.current_id == SYSTEM_THEME_ID
        assert manager.resolved_id == "light"
        assert json.loads((tmp_path / "theme.json").read_text())["theme"] == "system"
    finally:
        manager.apply_theme("dark")


def test_system_theme_display_data_uses_resolved_palette(monkeypatch):
    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    monkeypatch.setattr(
        themes, "_system_palette_colors",
        lambda base: dict(base["colors"]))

    data = get_theme_data(SYSTEM_THEME_ID)

    assert data["name"] == "System"
    assert data["colors"]["BG"] == THEMES["light"]["colors"]["BG"]


def test_system_theme_uses_live_palette_roles(monkeypatch):
    from PyQt6.QtGui import QColor, QPalette
    from PyQt6.QtWidgets import QApplication

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#292A2D"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#35363A"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#3C4043"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#E8EAED"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#F1F3F4"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#8AB4F8"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9AA0A6"))

    class _App:
        def palette(self):
            return palette

    monkeypatch.setattr(
        QApplication, "instance", staticmethod(lambda: _App()))
    monkeypatch.setattr(themes, "system_theme_id", lambda: "dark")

    data = get_theme_data(SYSTEM_THEME_ID)
    colors = data["colors"]

    assert data["is_dark"] is True
    assert colors["BG"] == "#202124"
    assert colors["SURFACE"] == "#292A2D"
    assert colors["TEXT"] == "#F1F3F4"
    assert colors["TEXT_ON_ACCENT"] == "#202124"
    assert colors["ACCENT"] == "#8AB4F8"
    assert colors["NEON"] == "#8AB4F8"
    assert colors["BORDER_FOCUS"] == "rgba(138, 180, 248, 0.550)"
    assert colors["OVERLAY_06"] == "rgba(232, 234, 237, 0.060)"
    assert colors["ACCENT_08"] == "rgba(138, 180, 248, 0.080)"


def test_system_font_families_use_os_fonts(monkeypatch):
    from PyQt6.QtGui import QFont, QFontDatabase
    from PyQt6.QtWidgets import QApplication

    class _App:
        def font(self):
            return QFont("Fake UI")

    monkeypatch.setattr(
        QApplication, "instance", staticmethod(lambda: _App()))

    def _system_font(kind):
        if kind == QFontDatabase.SystemFont.FixedFont:
            return QFont("Test Mono")
        return QFont("Test Sans")

    monkeypatch.setattr(
        QFontDatabase, "systemFont", staticmethod(_system_font))

    families = themes.system_font_families()

    assert families is not None
    assert families[0].startswith("'Test Sans'")
    assert families[1].startswith("'Test Mono'")


def test_manager_applies_system_fonts_and_restores_defaults(
        tmp_path, monkeypatch):
    from neoarch.frontend import tokens

    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    monkeypatch.setattr(
        themes, "system_font_families",
        lambda: ("'Test Sans', sans-serif", "'Test Mono', monospace"))
    monkeypatch.setattr(themes, "system_font_scale", lambda: 1.0)

    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    try:
        assert manager.apply_theme(SYSTEM_THEME_ID)
        assert tokens.Fonts.FAMILY == "'Test Sans', sans-serif"
        assert tokens.Fonts.MONO == "'Test Mono', monospace"
        assert tokens.Fonts.BASE == "13px"
    finally:
        manager.apply_theme("dark")

    assert tokens.Fonts.FAMILY == tokens.Fonts.DEFAULT_FAMILY
    assert tokens.Fonts.MONO == tokens.Fonts.DEFAULT_MONO


def test_manager_applies_system_metrics_and_restores_defaults(
        tmp_path, monkeypatch):
    from neoarch.frontend import tokens

    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    monkeypatch.setattr(themes, "system_metric_scale", lambda: 0.85)
    monkeypatch.setattr(themes, "system_scrollbar_width", lambda: 12)

    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    try:
        assert manager.apply_theme(SYSTEM_THEME_ID)
        assert tokens.Radii.SM == "3"
        assert tokens.Radii.MD == "7"
        assert tokens.Spacing.SM == "7"
        assert tokens.Scrollbar.WIDTH == "12"
        assert tokens.Scrollbar.RADIUS == "6"
        assert tokens.Scrollbar.MARGIN == "3"
        assert tokens.Scrollbar.MIN_LEN == "36"
    finally:
        manager.apply_theme("dark")

    assert tokens.Radii.SM == tokens.DEFAULT_RADII["SM"]
    assert tokens.Radii.MD == tokens.DEFAULT_RADII["MD"]
    assert tokens.Spacing.SM == tokens.DEFAULT_SPACING["SM"]
    assert tokens.Scrollbar.WIDTH == tokens.DEFAULT_SCROLLBAR["WIDTH"]
    assert tokens.Scrollbar.RADIUS == tokens.DEFAULT_SCROLLBAR["RADIUS"]
    assert tokens.Scrollbar.MARGIN == tokens.DEFAULT_SCROLLBAR["MARGIN"]
    assert tokens.Scrollbar.MIN_LEN == tokens.DEFAULT_SCROLLBAR["MIN_LEN"]


def test_failed_theme_application_restores_tokens(
        tmp_path, monkeypatch, qapp):
    from neoarch.frontend import tokens

    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    assert manager.apply_theme("dark")
    baseline = {
        "bg": tokens.Colors.BG,
        "radii_sm": tokens.Radii.SM,
        "spacing_sm": tokens.Spacing.SM,
        "scrollbar": tokens.Scrollbar.WIDTH,
    }

    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    monkeypatch.setattr(themes, "system_metric_scale", lambda: 0.5)
    monkeypatch.setattr(themes, "system_scrollbar_width", lambda: 14)

    def _fail():
        raise RuntimeError("stylesheet failed")

    monkeypatch.setattr(tokens.QSS, "regenerate", _fail)
    with pytest.raises(RuntimeError):
        manager.apply_theme(SYSTEM_THEME_ID)

    assert manager.current_id == "dark"
    assert tokens.Colors.BG == baseline["bg"]
    assert tokens.Radii.SM == baseline["radii_sm"]
    assert tokens.Spacing.SM == baseline["spacing_sm"]
    assert tokens.Scrollbar.WIDTH == baseline["scrollbar"]


def test_system_change_is_debounced(tmp_path, qapp, monkeypatch):
    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    manager._current_id = SYSTEM_THEME_ID
    calls = []
    monkeypatch.setattr(
        manager, "apply_theme",
        lambda theme_id: calls.append(theme_id) or True)

    manager._on_system_color_scheme_changed()

    assert calls == []
    assert manager._system_update_timer.isActive()

    manager._apply_system_update()

    assert calls == [SYSTEM_THEME_ID]


def test_system_palette_raises_low_contrast_borders(monkeypatch, qapp):
    from PyQt6.QtGui import QColor, QPalette
    from PyQt6.QtWidgets import QApplication

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#EEEEEE"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#EEEEEE"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3355FF"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#DDDDDD"))

    class _App:
        def palette(self):
            return palette

    monkeypatch.setattr(
        QApplication, "instance", staticmethod(lambda: _App()))
    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")

    border = get_theme_data(SYSTEM_THEME_ID)["colors"]["BORDER"]
    alpha = float(re.search(r", ([0-9.]+)\)$", border).group(1))

    assert alpha > 0.10


def test_load_saved_defaults_to_system(tmp_path, monkeypatch):
    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "missing.json")
    try:
        manager.load_saved()
        assert manager.current_id == SYSTEM_THEME_ID
        assert manager.resolved_id == "light"
    finally:
        manager.apply_theme("dark")


def test_system_theme_uses_palette_when_color_scheme_unknown(monkeypatch):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QPalette
    from PyQt6.QtWidgets import QApplication

    class _Hints:
        def colorScheme(self):
            return Qt.ColorScheme.Unknown

    class _Palette:
        def color(self, role):
            assert role == QPalette.ColorRole.Window
            return QColor("#FFFFFF")

    class _App:
        def styleHints(self):
            return _Hints()

        def palette(self):
            return _Palette()

    monkeypatch.setattr(QApplication, "instance", staticmethod(lambda: _App()))

    assert themes.system_theme_id() == "light"
