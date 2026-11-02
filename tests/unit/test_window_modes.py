"""Window-mode persistence and theme hand-off tests."""

from neoarch.backend.services.settings import (
    DEFAULT_SETTINGS,
    DEFAULT_WINDOW_MODE,
    WINDOW_MODE_NEOARCH,
    WINDOW_MODE_SYSTEM,
)
from neoarch.frontend.main_window import ArchPkgManagerUniGetUI
from neoarch.frontend.themes import SYSTEM_THEME_ID


class _FakeThemeManager:
    def __init__(self, current_id):
        self.current_id = current_id
        self.applied = []

    def apply_theme(self, theme_id):
        self.applied.append(theme_id)
        self.current_id = theme_id
        return True


def _fake_window(mode, theme_id):
    window = ArchPkgManagerUniGetUI.__new__(ArchPkgManagerUniGetUI)
    window.settings = {
        'window_mode': mode,
        'neoarch_theme': theme_id,
    }
    window._theme_manager = _FakeThemeManager(theme_id)
    window.saved = 0
    window.flags = []
    window.effects = 0
    window.save_settings = lambda: setattr(window, 'saved', window.saved + 1)
    window._apply_window_mode_flags = (
        lambda mode, initial=False: window.flags.append(mode))
    window.apply_window_effects = lambda: setattr(
        window, 'effects', window.effects + 1)
    window.rebuild_ui = lambda: None
    return window


def test_default_window_mode_is_native_system():
    assert DEFAULT_WINDOW_MODE == WINDOW_MODE_SYSTEM
    assert DEFAULT_SETTINGS['window_mode'] == WINDOW_MODE_SYSTEM
    assert DEFAULT_SETTINGS['neoarch_theme'] == ''
    assert DEFAULT_SETTINGS['window_system_transparency'] is False


def test_switch_to_native_preserves_neoarch_theme_and_applies_system():
    window = _fake_window(WINDOW_MODE_NEOARCH, 'dracula')

    ArchPkgManagerUniGetUI.set_window_mode(window, WINDOW_MODE_SYSTEM)

    assert window.settings['window_mode'] == WINDOW_MODE_SYSTEM
    assert window.settings['neoarch_theme'] == 'dracula'
    assert window._theme_manager.applied == [SYSTEM_THEME_ID]
    assert window.flags == [WINDOW_MODE_SYSTEM]
    assert window.effects == 1
    assert window.saved == 1


def test_switch_back_to_neoarch_restores_saved_theme():
    window = _fake_window(WINDOW_MODE_SYSTEM, 'nord')

    ArchPkgManagerUniGetUI.set_window_mode(window, WINDOW_MODE_NEOARCH)

    assert window.settings['window_mode'] == WINDOW_MODE_NEOARCH
    assert window._theme_manager.applied == ['nord']
    assert window.flags == [WINDOW_MODE_NEOARCH]
    assert window.effects == 1


def test_switch_to_native_does_not_save_system_as_a_neoarch_theme():
    window = _fake_window(WINDOW_MODE_NEOARCH, 'dracula')
    window._theme_manager.current_id = SYSTEM_THEME_ID

    ArchPkgManagerUniGetUI.set_window_mode(window, WINDOW_MODE_SYSTEM)

    assert window.settings['neoarch_theme'] == 'dracula'
    assert window._theme_manager.applied == [SYSTEM_THEME_ID]


def test_switch_back_to_neoarch_replaces_a_stale_system_theme():
    window = _fake_window(WINDOW_MODE_SYSTEM, SYSTEM_THEME_ID)

    ArchPkgManagerUniGetUI.set_window_mode(window, WINDOW_MODE_NEOARCH)

    assert window.settings['neoarch_theme'] == 'dark'
    assert window._theme_manager.applied == ['dark']


def test_switch_back_without_saved_theme_uses_dark():
    window = _fake_window(WINDOW_MODE_SYSTEM, '')

    ArchPkgManagerUniGetUI.set_window_mode(window, WINDOW_MODE_NEOARCH)

    assert window._theme_manager.applied == ['dark']


def test_unknown_window_mode_is_ignored():
    window = _fake_window(WINDOW_MODE_SYSTEM, 'dark')

    ArchPkgManagerUniGetUI.set_window_mode(window, 'bogus')

    assert window.settings['window_mode'] == WINDOW_MODE_SYSTEM
    assert window.saved == 0
    assert window.flags == []


def _flag_window(transparency):
    from PyQt6.QtCore import Qt

    window = ArchPkgManagerUniGetUI.__new__(ArchPkgManagerUniGetUI)
    window.settings = {
        'window_mode': WINDOW_MODE_SYSTEM,
        'window_system_transparency': transparency,
    }
    window._windowed_flags = 1
    window._frameless_flags = 2
    window._title_bar = None
    window.windowFlags = lambda: 1
    window.isVisible = lambda: False
    window.isMaximized = lambda: False
    window.geometry = lambda: None
    window.setWindowFlags = lambda flags: None
    attributes = {}
    window.setAttribute = (
        lambda attribute, value: attributes.__setitem__(attribute, value))
    return window, attributes, Qt


def test_native_transparency_enables_translucent_background():
    window, attributes, Qt = _flag_window(True)

    ArchPkgManagerUniGetUI._apply_window_mode_flags(
        window, WINDOW_MODE_SYSTEM)

    assert attributes[Qt.WidgetAttribute.WA_TranslucentBackground] is True


def test_native_mode_without_transparency_is_opaque():
    window, attributes, Qt = _flag_window(False)

    ArchPkgManagerUniGetUI._apply_window_mode_flags(
        window, WINDOW_MODE_SYSTEM)

    assert attributes[Qt.WidgetAttribute.WA_TranslucentBackground] is False


def test_native_transparency_uses_saved_opacity():
    from neoarch.frontend import tokens

    window = ArchPkgManagerUniGetUI.__new__(ArchPkgManagerUniGetUI)
    window.settings = {
        'window_mode': WINDOW_MODE_SYSTEM,
        'window_system_transparency': True,
        'window_opacity': 0.55,
        'window_glow': False,
        'window_radius': 8,
    }
    window._window_mode = lambda: WINDOW_MODE_SYSTEM
    window.centralWidget = lambda: None
    window.setStyleSheet = lambda stylesheet: None
    attributes = {}
    window.setAttribute = (
        lambda attribute, value: attributes.__setitem__(attribute, value))
    old_effects = (
        tokens.WINDOW_OPACITY, tokens.WINDOW_GLOW, tokens.WINDOW_RADIUS)
    try:
        ArchPkgManagerUniGetUI.apply_window_effects(window)
        assert tokens.WINDOW_OPACITY == 0.55
        from PyQt6.QtCore import Qt
        assert attributes[Qt.WidgetAttribute.WA_TranslucentBackground] is True
    finally:
        (tokens.WINDOW_OPACITY, tokens.WINDOW_GLOW,
         tokens.WINDOW_RADIUS) = old_effects
