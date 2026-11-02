"""Widget-level tests for the Appearance settings page and window effects."""

import json

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

from neoarch.backend.services import settings as settings_service
from neoarch.backend.services.settings import (
    WINDOW_MODE_NEOARCH,
    WINDOW_MODE_SYSTEM,
)
from neoarch.frontend.mixins.settings import _SettingsMixin
from neoarch.frontend.views.settings_appearance import AppearanceSettingsWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeThemeManager:
    def __init__(self):
        self.current_id = "dark"

    def apply_theme(self, theme_id):
        self.current_id = theme_id
        return True

    def reload(self):
        return True


class _FakeApp(QWidget):
    def __init__(self, mode=WINDOW_MODE_SYSTEM, transparency=True):
        super().__init__()
        self.settings = {
            "theme": "dark",
            "window_mode": mode,
            "neoarch_theme": "",
            "window_system_transparency": transparency,
            "window_glow": False,
            "window_radius": 8,
            "window_opacity": 0.75,
        }
        self._theme_manager = _FakeThemeManager()
        self.refreshed = 0
        self.selected_mode = None

    def update_setting(self, key, value):
        self.settings[key] = value

    def set_window_mode(self, mode):
        self.selected_mode = mode
        self.settings["window_mode"] = mode

    def _window_mode(self):
        return self.settings["window_mode"]

    def refresh_window_mode(self):
        self.refreshed += 1

    def apply_window_effects(self):
        self.refreshed += 1


def test_native_mode_shows_and_persists_transparency_toggle(qapp):
    app = _FakeApp(WINDOW_MODE_SYSTEM, transparency=True)

    widget = AppearanceSettingsWidget(app)

    assert widget._system_transparency_toggle.isChecked()
    widget._system_transparency_toggle.setChecked(False)

    assert app.settings["window_system_transparency"] is False
    assert app.refreshed == 1


def test_neoarch_theme_list_omits_the_native_system_row(qapp):
    from neoarch.frontend.themes import SYSTEM_THEME_ID, THEMES

    app = _FakeApp(WINDOW_MODE_NEOARCH)

    widget = AppearanceSettingsWidget(app)

    assert SYSTEM_THEME_ID not in widget._cards
    assert set(widget._cards) == set(THEMES) - {SYSTEM_THEME_ID}


def test_stale_system_theme_is_not_left_unselected(qapp):
    from neoarch.frontend.themes import SYSTEM_THEME_ID

    app = _FakeApp(WINDOW_MODE_NEOARCH)
    app._theme_manager.current_id = SYSTEM_THEME_ID

    widget = AppearanceSettingsWidget(app)

    assert "dark" in widget._cards


def test_neoarch_mode_hides_transparency_toggle(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)

    widget = AppearanceSettingsWidget(app)

    assert not hasattr(widget, "_system_transparency_toggle")


def test_apply_window_effects_updates_real_widget(qapp):
    from PyQt6.QtCore import Qt

    from neoarch.frontend import tokens

    class _Window(QWidget):
        def __init__(self, transparency):
            super().__init__()
            self.settings = {
                "window_mode": WINDOW_MODE_SYSTEM,
                "window_system_transparency": transparency,
                "window_opacity": 0.60,
                "window_glow": False,
                "window_radius": 8,
            }

        def _window_mode(self):
            return WINDOW_MODE_SYSTEM

        def centralWidget(self):
            return None

    window = _Window(True)
    old_effects = (
        tokens.WINDOW_OPACITY, tokens.WINDOW_GLOW, tokens.WINDOW_RADIUS)
    try:
        _SettingsMixin.apply_window_effects(window)
        assert window.testAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground)
        assert tokens.WINDOW_OPACITY == 0.60

        window.settings["window_system_transparency"] = False
        _SettingsMixin.apply_window_effects(window)
        assert not window.testAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground)
        assert tokens.WINDOW_OPACITY == 1.0
    finally:
        (tokens.WINDOW_OPACITY, tokens.WINDOW_GLOW,
         tokens.WINDOW_RADIUS) = old_effects


def test_import_export_preserves_system_transparency(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"

    class _ExportApp:
        def __init__(self):
            self.settings = {
                "window_system_transparency": True,
                "window_mode": WINDOW_MODE_SYSTEM,
            }
            self.rebuilt = False

        def log(self, _message):
            pass

        def _show_message(self, _title, _message):
            pass

        def build_settings_ui(self):
            self.rebuilt = True

    monkeypatch.setattr(
        settings_service.QFileDialog, "getSaveFileName",
        staticmethod(lambda *args: (str(path), "")))
    monkeypatch.setattr(
        settings_service, "save_settings",
        lambda *args, **kwargs: None)

    app = _ExportApp()
    settings_service.export_settings(app)

    assert json.loads(path.read_text())["window_system_transparency"] is True

    imported = _ExportApp()
    imported.settings = {}
    monkeypatch.setattr(
        settings_service.QFileDialog, "getOpenFileName",
        staticmethod(lambda *args: (str(path), "")))
    settings_service.import_settings(imported)

    assert imported.settings["window_system_transparency"] is True
    assert imported.rebuilt is True
