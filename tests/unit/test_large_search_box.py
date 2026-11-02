"""Tests for the Discover dashboard action buttons."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from PyQt6.QtWidgets import QApplication, QPushButton

from neoarch.frontend.components.large_search_box import LargeSearchBox
from neoarch.frontend.themes import ThemeManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _action_buttons():
    box = LargeSearchBox.__new__(LargeSearchBox)
    box._on_update_all = lambda: None
    box._on_refresh = lambda: None
    box._on_clean = lambda: None
    row = box._actions_row()
    buttons = []
    for index in range(row.count()):
        widget = row.itemAt(index).widget()
        if isinstance(widget, QPushButton):
            buttons.append(widget)
    return buttons


def _average_luminance(icon):
    image = icon.pixmap(17, 17).toImage()
    values = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() > 200:
                values.append(
                    0.2126 * color.red()
                    + 0.7152 * color.green()
                    + 0.0722 * color.blue()
                )
    return sum(values) / len(values) if values else None


def test_discover_action_icons_are_visible_in_light_theme(qapp, monkeypatch):
    manager = ThemeManager()
    monkeypatch.setattr(manager, "_save", lambda: None)
    try:
        assert manager.apply_theme("light")
        buttons = _action_buttons()
        assert len(buttons) == 3
        for button in buttons:
            luminance = _average_luminance(button.icon())
            assert luminance is not None
            assert luminance < 128
    finally:
        manager.apply_theme("dark")
