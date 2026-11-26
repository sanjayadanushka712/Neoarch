"""Wallpaper-enabled window frame tests."""

from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from neoarch.frontend.components.app_window_frame import AppWindowFrame
from neoarch.frontend.themes import BUILTIN_THEME_DIR


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_frame_loads_and_clears_wallpaper(qapp):
    image = Path(BUILTIN_THEME_DIR) / "backgrounds" / "neoarch-pro.jpg"
    frame = AppWindowFrame()
    frame.resize(320, 180)

    frame.set_theme_background({
        "image": str(image),
        "blur": 4,
        "opacity": 1.0,
        "position": "center",
        "scrim": "rgba(0, 0, 0, 0.4)",
    })

    assert frame._source is not None
    assert frame._blurred is not None
    assert not frame.grab().isNull()

    frame.set_theme_background(None)

    assert frame._source is None
    assert frame._blurred is None


def test_frame_ignores_missing_wallpaper(qapp):
    frame = AppWindowFrame()
    frame.resize(200, 120)

    frame.set_theme_background({
        "image": "/missing/neoarch-background.jpg",
        "blur": 8,
    })

    assert frame._source is None
    assert not frame.grab().isNull()


def test_frame_applies_window_opacity_to_wallpaper(qapp):
    from PyQt6.QtCore import Qt

    from neoarch.frontend import tokens

    image = Path(BUILTIN_THEME_DIR) / "backgrounds" / "neoarch-pro.jpg"
    old_opacity = tokens.WINDOW_OPACITY
    try:
        alphas = []
        for opacity in (1.0, 0.25):
            tokens.WINDOW_OPACITY = opacity
            frame = AppWindowFrame()
            frame.resize(320, 180)
            frame.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground, True)
            frame.setStyleSheet("background: transparent;")
            frame.set_theme_background({
                "image": str(image),
                "blur": 4,
                "opacity": 1.0,
                "position": "center",
                "scrim": "rgba(0, 0, 0, 0.4)",
            })
            alphas.append(frame.grab().toImage().pixelColor(160, 90).alpha())

        assert alphas[0] > 240
        assert alphas[1] < 120
    finally:
        tokens.WINDOW_OPACITY = old_opacity


def test_frame_applies_window_opacity_to_plain_background(qapp):
    from PyQt6.QtCore import Qt

    from neoarch.frontend import tokens

    old_opacity = tokens.WINDOW_OPACITY
    old_radius = tokens.WINDOW_RADIUS
    try:
        tokens.WINDOW_RADIUS = 8
        alphas = []
        for opacity in (1.0, 0.25):
            tokens.WINDOW_OPACITY = opacity
            frame = AppWindowFrame()
            frame.resize(320, 180)
            frame.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground, True)
            frame.setStyleSheet("background: transparent;")
            alphas.append(frame.grab().toImage().pixelColor(160, 90).alpha())

        assert alphas[0] > 240
        assert alphas[1] < 120
    finally:
        tokens.WINDOW_OPACITY = old_opacity
        tokens.WINDOW_RADIUS = old_radius
