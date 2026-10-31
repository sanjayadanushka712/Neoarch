"""Tests for the package-detail screenshot carousel."""

import os
import sys
import time

import pytest
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from neoarch.frontend.components.screenshot_carousel import (  # noqa: E402
    ScreenshotCarousel)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _pixmap(color):
    pixmap = QPixmap(20, 20)
    pixmap.fill(QColor(color))
    return pixmap


def _slides(*colors):
    return [{"caption": f"shot {i}", "pixmap": _pixmap(c)}
            for i, c in enumerate(colors)]


def test_empty_slides_hide_controls(qapp):
    carousel = ScreenshotCarousel()
    carousel.show()
    carousel.set_slides(carousel._request_id, [])
    assert carousel.count == 0
    assert carousel.prev_btn.isVisible() is False
    assert carousel.next_btn.isVisible() is False
    assert carousel.counter_label.text() == ""
    carousel.deleteLater()


def test_navigation_moves_between_slides(qapp):
    carousel = ScreenshotCarousel()
    carousel.show()
    carousel.set_slides(carousel._request_id,
                        _slides("red", "green", "blue"))
    assert carousel.count == 3
    assert carousel.current_index == 0
    assert carousel.counter_label.text() == "1 / 3"
    assert carousel.prev_btn.isEnabled() is False
    assert carousel.next_btn.isEnabled() is True

    carousel.show_next()
    assert carousel.current_index == 1
    assert carousel.caption_label.text() == "shot 1"
    assert carousel.prev_btn.isEnabled() is True

    carousel.show_next()
    carousel.show_next()
    assert carousel.current_index == 2
    assert carousel.next_btn.isEnabled() is False

    carousel.show_previous()
    assert carousel.current_index == 1
    carousel.deleteLater()


def test_single_slide_hides_arrows(qapp):
    carousel = ScreenshotCarousel()
    carousel.show()
    carousel.set_slides(carousel._request_id, _slides("red"))
    assert carousel.count == 1
    assert carousel.prev_btn.isVisible() is False
    assert carousel.next_btn.isVisible() is False
    assert carousel.counter_label.text() == ""
    carousel.deleteLater()


def test_stale_results_are_ignored(qapp):
    carousel = ScreenshotCarousel()
    carousel.show()
    carousel._request_id = 3
    carousel.set_slides(2, _slides("red"))
    assert carousel.count == 0
    carousel.deleteLater()


def test_load_fetches_in_background(qapp, tmp_path):
    source = _pixmap("red")
    path = tmp_path / "shot.png"
    source.save(str(path), "PNG")
    data = path.read_bytes()

    carousel = ScreenshotCarousel(
        fetcher=lambda app_id: [{"caption": "Loaded", "data": data}])
    carousel.show()
    carousel.load("org.example.App")
    deadline = time.time() + 3
    while carousel.count == 0 and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    assert carousel.count == 1
    assert carousel.caption_label.text() == "Loaded"
    carousel.deleteLater()


def test_loaded_signal_reports_count(qapp):
    carousel = ScreenshotCarousel()
    seen = []
    carousel.loaded.connect(seen.append)
    carousel.set_slides(carousel._request_id, _slides("red", "green"))
    assert seen[-1] == 2
    carousel.set_slides(carousel._request_id, [])
    assert seen[-1] == 0
    carousel.deleteLater()


def test_clear_resets_state(qapp):
    carousel = ScreenshotCarousel()
    carousel.show()
    carousel.set_slides(carousel._request_id, _slides("red", "green"))
    carousel.clear()
    assert carousel.count == 0
    assert carousel.current_index == 0
    assert carousel.image.text() == ""
    carousel.deleteLater()
