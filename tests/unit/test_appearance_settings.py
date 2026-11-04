"""Widget-level tests for the Appearance settings page and window effects."""

import json

import pytest
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget

from neoarch.backend.services import settings as settings_service
from neoarch.backend.services.settings import (
    WINDOW_MODE_NEOARCH,
    WINDOW_MODE_SYSTEM,
)
from neoarch.frontend.mixins.settings import _SettingsMixin
from neoarch.frontend.views.settings_appearance import AppearanceSettingsWidget


@pytest.fixture(autouse=True)
def isolated_trial_ledger(tmp_path, monkeypatch):
    """Keep trial state out of the real user data directory."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))


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


class _MessageSignal:
    def __init__(self, messages):
        self._messages = messages

    def emit(self, title, message):
        self._messages.append((title, message))


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
            "unlocked_pro_themes": [],
        }
        self._theme_manager = _FakeThemeManager()
        self.refreshed = 0
        self.previewed = 0
        self.saves = 0
        self.selected_mode = None
        self.messages = []
        self.show_message = _MessageSignal(self.messages)

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

    def preview_window_effects(self):
        self.previewed += 1

    def save_settings(self):
        self.saves += 1


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


def test_pro_themes_have_a_separate_section(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)

    widget = AppearanceSettingsWidget(app)

    assert "neoarch-pro" in widget._pro_cards
    assert "neoarch-pro-evergreen" in widget._pro_cards
    assert "neoarch-pro-ember" in widget._pro_cards
    assert "neoarch-pro-glacier" in widget._pro_cards
    assert "neoarch-pro-aero" in widget._pro_cards
    assert "neoarch-pro-lagoon" in widget._pro_cards
    assert "neoarch-pro-moss" in widget._pro_cards
    assert "neoarch-pro-sakura" in widget._pro_cards
    assert "neoarch-pro-crystal" in widget._pro_cards
    assert "neoarch-pro-endeavour" in widget._pro_cards
    assert "neoarch-pro-v4" in widget._pro_cards
    assert "neoarch-pro-halloween" in widget._pro_cards
    assert "neoarch-pro" in widget._cards
    assert widget._pro_cards["neoarch-pro"] is widget._cards["neoarch-pro"]
    assert (widget._pro_cards["neoarch-pro-evergreen"]
            is widget._cards["neoarch-pro-evergreen"])
    assert (widget._pro_cards["neoarch-pro-ember"]
            is widget._cards["neoarch-pro-ember"])
    assert (widget._pro_cards["neoarch-pro-glacier"]
            is widget._cards["neoarch-pro-glacier"])
    assert (widget._pro_cards["neoarch-pro-aero"]
            is widget._cards["neoarch-pro-aero"])
    assert (widget._pro_cards["neoarch-pro-lagoon"]
            is widget._cards["neoarch-pro-lagoon"])
    assert (widget._pro_cards["neoarch-pro-moss"]
            is widget._cards["neoarch-pro-moss"])
    assert (widget._pro_cards["neoarch-pro-sakura"]
            is widget._cards["neoarch-pro-sakura"])
    assert (widget._pro_cards["neoarch-pro-crystal"]
            is widget._cards["neoarch-pro-crystal"])
    assert (widget._pro_cards["neoarch-pro-endeavour"]
            is widget._cards["neoarch-pro-endeavour"])
    assert (widget._pro_cards["neoarch-pro-v4"]
            is widget._cards["neoarch-pro-v4"])
    assert (widget._pro_cards["neoarch-pro-halloween"]
            is widget._cards["neoarch-pro-halloween"])


def test_free_pro_themes_are_unlocked(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)

    widget = AppearanceSettingsWidget(app)

    assert not widget._pro_cards["neoarch-pro"].locked
    assert not widget._pro_cards["neoarch-pro-endeavour"].locked
    assert not widget._pro_cards["neoarch-pro-v4"].locked
    for theme_id in (
            "neoarch-pro-evergreen", "neoarch-pro-ember",
            "neoarch-pro-glacier", "neoarch-pro-aero",
            "neoarch-pro-lagoon", "neoarch-pro-moss",
            "neoarch-pro-sakura", "neoarch-pro-crystal",
            "neoarch-pro-halloween"):
        assert widget._pro_cards[theme_id].locked


def test_locked_pro_theme_does_not_apply_and_shows_message(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)

    widget = AppearanceSettingsWidget(app)
    widget._apply_theme("neoarch-pro-crystal")

    assert app._theme_manager.current_id == "dark"
    assert app.messages
    assert app.messages[-1][0] == "Locked theme"


def test_locked_pro_rows_have_password_unlock_controls(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)

    widget = AppearanceSettingsWidget(app)

    for theme_id in (
            "neoarch-pro-evergreen", "neoarch-pro-ember",
            "neoarch-pro-glacier", "neoarch-pro-aero",
            "neoarch-pro-lagoon", "neoarch-pro-moss",
            "neoarch-pro-sakura", "neoarch-pro-crystal",
            "neoarch-pro-halloween"):
        row = widget._pro_cards[theme_id]
        assert row.locked
        assert isinstance(row._unlock_edit, QLineEdit)
        assert row._unlock_edit.echoMode() == QLineEdit.EchoMode.Password
        assert row._unlock_button is not None
        assert row._trial_button is not None
        assert row._trial_label.isHidden()

    for theme_id in ("neoarch-pro", "neoarch-pro-endeavour",
                     "neoarch-pro-v4"):
        row = widget._pro_cards[theme_id]
        assert not row.locked
        assert row._unlock_edit is None
        assert row._unlock_button is None
        assert row._trial_button is None


def test_correct_unlock_code_unlocks_and_applies_theme(qapp, monkeypatch):
    import hashlib
    from neoarch.frontend import themes
    from neoarch.frontend.themes import UNLOCKED_PRO_SETTING

    password = "TestOnly-Crystal-123"
    salt = bytes.fromhex("00112233445566778899aabbccddeeff")
    iterations = 1_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations)
    monkeypatch.setitem(
        themes.PRO_UNLOCK_HASHES, "neoarch-pro-crystal",
        f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}")

    app = _FakeApp(WINDOW_MODE_NEOARCH)
    widget = AppearanceSettingsWidget(app)
    row = widget._pro_cards["neoarch-pro-crystal"]

    row._unlock_edit.setText(password)
    row._unlock_button.click()

    assert not row.locked
    assert row._unlock_box.isHidden()
    assert app.settings[UNLOCKED_PRO_SETTING] == ["neoarch-pro-crystal"]
    assert app._theme_manager.current_id == "neoarch-pro-crystal"


def test_trial_button_starts_and_persists_trial(qapp, tmp_path, monkeypatch):
    from neoarch.backend.services import pro_trials

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    app = _FakeApp(WINDOW_MODE_NEOARCH)
    widget = AppearanceSettingsWidget(app)
    row = widget._pro_cards["neoarch-pro-crystal"]

    row._trial_button.click()

    assert app._theme_manager.current_id == "neoarch-pro-crystal"
    assert pro_trials.TRIAL_SETTING in app.settings
    assert row.locked
    assert row._trial_button.isHidden()
    assert not row._trial_label.isHidden()
    assert "Trial:" in row._trial_label.text()
    assert not app.messages

    app._theme_manager.current_id = "dark"
    widget._apply_theme("neoarch-pro-crystal")
    assert app._theme_manager.current_id == "neoarch-pro-crystal"


def test_expired_trial_keeps_theme_locked(qapp, tmp_path, monkeypatch):
    import time

    from neoarch.backend.services import pro_trials

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    app = _FakeApp(WINDOW_MODE_NEOARCH)
    now = time.time()
    pro_trials.start_trial(
        app.settings, "neoarch-pro-moss",
        now=now - pro_trials.TRIAL_DURATION_SECONDS - 1)

    widget = AppearanceSettingsWidget(app)
    row = widget._pro_cards["neoarch-pro-moss"]

    assert row._trial_button.isHidden()
    assert row._trial_label.text() == "Trial ended"

    widget._apply_theme("neoarch-pro-moss")
    assert app._theme_manager.current_id == "dark"
    assert app.messages[-1][0] == "Locked theme"


def test_wrong_unlock_code_keeps_theme_locked(qapp):
    from neoarch.frontend.themes import UNLOCKED_PRO_SETTING

    app = _FakeApp(WINDOW_MODE_NEOARCH)
    widget = AppearanceSettingsWidget(app)
    row = widget._pro_cards["neoarch-pro-crystal"]

    row._unlock_edit.setText("wrong-code")
    row._unlock_button.click()

    assert row.locked
    assert app.settings[UNLOCKED_PRO_SETTING] == []
    assert app.messages[-1][0] == "Invalid unlock code"


def test_saved_unlock_is_restored_on_next_launch(qapp):
    from neoarch.frontend.themes import UNLOCKED_PRO_SETTING

    app = _FakeApp(WINDOW_MODE_NEOARCH)
    app.settings[UNLOCKED_PRO_SETTING] = ["neoarch-pro-moss"]

    widget = AppearanceSettingsWidget(app)
    row = widget._pro_cards["neoarch-pro-moss"]

    assert not row.locked
    assert row._unlock_edit is None
    widget._apply_theme("neoarch-pro-moss")
    assert app._theme_manager.current_id == "neoarch-pro-moss"
    assert not app.messages


def test_free_pro_theme_still_applies(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)

    widget = AppearanceSettingsWidget(app)
    widget._apply_theme("neoarch-pro-endeavour")

    assert app._theme_manager.current_id == "neoarch-pro-endeavour"
    assert not app.messages

    widget._apply_theme("neoarch-pro-v4")

    assert app._theme_manager.current_id == "neoarch-pro-v4"
    assert not app.messages


def test_glow_toggle_defaults_to_active_theme_effect(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)
    app._theme_manager.current_id = "neoarch-pro-endeavour"

    widget = AppearanceSettingsWidget(app)

    assert widget._glow_toggle.isChecked()


def test_explicit_glow_off_wins_over_theme_effect(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)
    app._theme_manager.current_id = "neoarch-pro-endeavour"
    app.settings["window_glow_explicit"] = True
    app.settings["window_glow"] = False

    widget = AppearanceSettingsWidget(app)

    assert not widget._glow_toggle.isChecked()


def test_toggling_glow_records_explicit_choice(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)
    app._theme_manager.current_id = "neoarch-pro-endeavour"

    widget = AppearanceSettingsWidget(app)
    widget._glow_toggle.setChecked(False)

    assert app.settings["window_glow_explicit"] is True
    assert app.settings["window_glow"] is False
    assert app.refreshed == 1


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


def test_wallpaper_theme_stays_transparent(qapp):
    from PyQt6.QtCore import Qt

    from neoarch.frontend import tokens

    class _Manager:
        current_id = "neoarch-pro"

    class _Window(QWidget):
        def __init__(self):
            super().__init__()
            self.settings = {
                "window_mode": WINDOW_MODE_NEOARCH,
                "window_opacity": 0.55,
                "window_glow": False,
                "window_radius": 8,
            }
            self._theme_manager = _Manager()

        def _window_mode(self):
            return WINDOW_MODE_NEOARCH

        def centralWidget(self):
            return None

    old_effects = (
        tokens.WINDOW_OPACITY,
        tokens.WINDOW_GLOW,
        tokens.WINDOW_RADIUS,
        tokens.WINDOW_BACKGROUND_ACTIVE,
    )
    try:
        window = _Window()
        _SettingsMixin.apply_window_effects(window)

        assert window.testAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground)
        assert tokens.WINDOW_OPACITY == 0.55
        assert tokens.WINDOW_BACKGROUND_ACTIVE is True
        assert "QFrame#appWindow" in tokens.DARK_STYLESHEET
        assert "background-color: transparent;" in tokens.DARK_STYLESHEET
    finally:
        (
            tokens.WINDOW_OPACITY,
            tokens.WINDOW_GLOW,
            tokens.WINDOW_RADIUS,
            tokens.WINDOW_BACKGROUND_ACTIVE,
        ) = old_effects
        tokens.rebuild_stylesheet()


def test_radius_slider_previews_without_full_restyle(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)
    widget = AppearanceSettingsWidget(app)
    before_previewed = app.previewed
    before_refreshed = app.refreshed
    value = widget._radius_slider.value() + 2

    widget._radius_slider.setValue(value)

    assert app.settings["window_radius"] == value
    assert app.previewed > before_previewed
    assert app.refreshed == before_refreshed


def test_opacity_slider_previews_without_full_restyle(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)
    widget = AppearanceSettingsWidget(app)
    before_previewed = app.previewed
    before_refreshed = app.refreshed
    value = widget._opacity_slider.value() - 5

    widget._opacity_slider.setValue(value)

    assert app.settings["window_opacity"] == value / 100.0
    assert app.previewed > before_previewed
    assert app.refreshed == before_refreshed


def test_window_sliders_persist_on_release(qapp):
    app = _FakeApp(WINDOW_MODE_NEOARCH)
    widget = AppearanceSettingsWidget(app)

    widget._radius_slider.sliderReleased.emit()
    widget._opacity_slider.sliderReleased.emit()

    assert app.saves == 2


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


def test_apply_window_effects_uses_theme_defined_glow(qapp):
    from neoarch.frontend import tokens
    from neoarch.frontend.themes import get_theme_effects

    class _ThemeManager:
        current_id = "neoarch-pro-endeavour"

    class _Window(QWidget):
        def __init__(self, explicit=None):
            super().__init__()
            self._theme_manager = _ThemeManager()
            self.settings = {
                "window_mode": WINDOW_MODE_NEOARCH,
                "window_system_transparency": False,
                "window_opacity": 0.75,
                "window_glow": False,
                "window_glow_explicit": explicit,
                "window_radius": 8,
            }

        def _window_mode(self):
            return WINDOW_MODE_NEOARCH

        def centralWidget(self):
            return None

    window = _Window()
    glow = get_theme_effects("neoarch-pro-endeavour")["glow"]
    old = (tokens.WINDOW_GLOW, tokens.WINDOW_GLOW_COLOR,
           tokens.WINDOW_GLOW_WIDTH, tokens.WINDOW_GLOW_OPACITY,
           tokens.WINDOW_BACKGROUND_ACTIVE)
    try:
        _SettingsMixin.apply_window_effects(window)
        assert tokens.WINDOW_GLOW is True
        assert tokens.WINDOW_GLOW_COLOR == glow["color"]
        assert tokens.WINDOW_GLOW_WIDTH == glow["width"]
        assert tokens.WINDOW_GLOW_OPACITY == glow["opacity"]
        assert tokens.WINDOW_BACKGROUND_ACTIVE is True

        window.settings["window_glow_explicit"] = True
        _SettingsMixin.apply_window_effects(window)
        assert tokens.WINDOW_GLOW is False
    finally:
        (tokens.WINDOW_GLOW, tokens.WINDOW_GLOW_COLOR,
         tokens.WINDOW_GLOW_WIDTH, tokens.WINDOW_GLOW_OPACITY,
         tokens.WINDOW_BACKGROUND_ACTIVE) = old
        tokens.rebuild_stylesheet()


def test_apply_window_effects_skips_before_settings_loaded(qapp):
    class _Uninitialised:
        pass

    assert _SettingsMixin.apply_window_effects(_Uninitialised()) is None
