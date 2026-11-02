"""Tests for tray lifecycle, close-to-tray, and --minimized startup."""

from types import SimpleNamespace

import pytest
from PyQt6.QtWidgets import QApplication

from neoarch.backend.services.settings import DEFAULT_SETTINGS
from neoarch.frontend.components.tray_icon import TrayIcon
from neoarch.frontend.main_window import ArchPkgManagerUniGetUI
from neoarch.main import _parse_args
from neoarch.resources.paths import APP_ICON


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeTray:
    def __init__(self):
        self.visible = True
        self.hidden = 0
        self.messages = []

    def isVisible(self):
        return self.visible

    def hide(self):
        self.hidden += 1

    def showMessage(self, title, message, icon, timeout):
        self.messages.append((title, message, timeout))


def test_cli_parses_minimized_flags():
    assert _parse_args([]) == (False, None)
    assert _parse_args(["--minimized"]) == (True, None)
    assert _parse_args(["--tray"]) == (True, None)
    assert _parse_args(["--bogus"])[1].startswith("Unknown option")


def test_tray_lifecycle_defaults_are_opt_in():
    assert DEFAULT_SETTINGS["start_minimized"] is False
    assert DEFAULT_SETTINGS["close_to_tray"] is False


def test_close_to_tray_requires_setting_and_visible_tray():
    fake = SimpleNamespace(
        settings={"close_to_tray": True}, tray_icon=_FakeTray())
    assert ArchPkgManagerUniGetUI.close_to_tray_active(fake) is True

    fake.settings["close_to_tray"] = False
    assert ArchPkgManagerUniGetUI.close_to_tray_active(fake) is False

    fake.settings["close_to_tray"] = True
    fake.tray_icon.visible = False
    assert ArchPkgManagerUniGetUI.close_to_tray_active(fake) is False


def test_tray_notice_is_shown_once():
    fake = SimpleNamespace(
        _tray_notice_shown=False, tray_icon=_FakeTray())

    ArchPkgManagerUniGetUI.show_tray_notice(fake)
    ArchPkgManagerUniGetUI.show_tray_notice(fake)

    assert len(fake.tray_icon.messages) == 1
    assert fake.tray_icon.messages[0][2] == 4000


def test_request_quit_bypasses_close_to_tray():
    fake = SimpleNamespace(
        _force_quit=False, tray_icon=_FakeTray(), closed=False)

    def _close():
        fake.closed = True

    fake.close = _close
    ArchPkgManagerUniGetUI.request_quit(fake)

    assert fake._force_quit is True
    assert fake.tray_icon.hidden == 1
    assert fake.closed is True


def test_tray_quit_uses_window_request_quit(qapp):
    class _App:
        def __init__(self):
            self.requested = 0

        def request_quit(self):
            self.requested += 1

    app = _App()
    tray = TrayIcon(app, APP_ICON)
    tray.quit_app()
    assert app.requested == 1
    tray.deleteLater()
