"""Tests for the system tray icon and its update badge."""

import os
import sys

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from neoarch.frontend.components.tray_icon import (  # noqa: E402
    TrayIcon, badge_pixmap, tray_available)
from neoarch.resources.paths import APP_ICON  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _base():
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(20, 20, 20))
    return pixmap


def test_badge_zero_leaves_icon_plain(qapp):
    pixmap = badge_pixmap(_base(), 0)
    assert pixmap.size().width() == 64
    assert pixmap.toImage().pixelColor(60, 60) == QColor(20, 20, 20)


def test_badge_paints_corner_for_count(qapp):
    pixmap = badge_pixmap(_base(), 3)
    assert pixmap.toImage().pixelColor(56, 56) != QColor(20, 20, 20)


def test_badge_caps_large_counts(qapp):
    pixmap = badge_pixmap(_base(), 150)
    assert not pixmap.isNull()
    assert pixmap.size().width() == 64


def test_badge_handles_invalid_count(qapp):
    pixmap = badge_pixmap(_base(), None)
    assert pixmap.toImage().pixelColor(60, 60) == QColor(20, 20, 20)


class _FakeApp:
    def __init__(self):
        self.shown = 0
        self.navigated = []

    def showNormal(self):
        self.shown += 1

    def raise_(self):
        self.shown += 1

    def activateWindow(self):
        pass

    def _handle_nav(self, view_id):
        self.navigated.append(view_id)


def test_tray_menu_actions_and_badge(qapp):
    fake = _FakeApp()
    tray = TrayIcon(fake, APP_ICON)
    tray.set_update_count(5)
    assert tray.update_count() == 5
    assert "5" in tray.toolTip()

    tray.open_action.trigger()
    assert fake.shown >= 1
    tray.check_action.trigger()
    assert fake.navigated == ["updates"]

    tray.set_update_count(0)
    assert tray.update_count() == 0
    assert tray.toolTip() == "NeoArch"
    tray.deleteLater()


def test_tray_available_returns_bool(qapp):
    assert isinstance(tray_available(), bool)


def test_set_updates_count_updates_tray(qapp):
    from neoarch.frontend.mixins.views import _ViewsMixin

    fake = _FakeApp()
    fake.large_search_box = None
    fake.nav_badges = {}
    fake.nav_buttons = {}
    fake.tray_icon = TrayIcon(fake, APP_ICON)
    _ViewsMixin.set_updates_count(fake, 4)
    assert fake.tray_icon.update_count() == 4
    fake.tray_icon.deleteLater()


def test_tray_activation_shows_window(qapp):
    fake = _FakeApp()
    tray = TrayIcon(fake, APP_ICON)
    tray._on_activated(tray.ActivationReason.Trigger)
    assert fake.shown >= 1
    tray.deleteLater()
