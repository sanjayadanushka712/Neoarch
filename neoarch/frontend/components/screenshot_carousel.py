"""Screenshot carousel for the package detail card.

Fetches Flathub AppStream screenshots off the UI thread, downloads the
images, and renders them with previous/next controls and a caption.
"""

import threading
import urllib.request

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from neoarch.backend.services.i18n import _
from neoarch.backend.services.screenshots import flathub_screenshots
from neoarch.frontend.tokens import Colors, Fonts

__all__ = ["ScreenshotCarousel"]

_MAX_SLIDES = 8
_IMAGE_HEIGHT = 150


def _download(url: str, timeout: int = 10) -> bytes:
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "NeoArch"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except Exception:
        return b""


def _nav_style() -> str:
    return (
        f"QPushButton {{ background: rgba(255,255,255,0.08);"
        f" border: 1px solid {Colors.BORDER}; border-radius: 13px;"
        f" color: {Colors.TEXT}; font-size: 16px; padding: 0; }}"
        f"QPushButton:hover {{ background: rgba(255,255,255,0.14); }}"
        f"QPushButton:disabled {{ color: {Colors.TEXT_3};"
        f" border-color: rgba(255,255,255,0.04); }}"
    )


class ScreenshotCarousel(QFrame):
    """A small image carousel fed by Flathub screenshots."""

    slides_ready = pyqtSignal(int, list)
    loaded = pyqtSignal(int)

    def __init__(self, parent=None, fetcher=None):
        super().__init__(parent)
        self._fetcher = fetcher or flathub_screenshots
        self._slides = []
        self._index = 0
        self._request_id = 0
        self.setStyleSheet("background: transparent; border: none;")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.prev_btn = QPushButton("‹")
        self.prev_btn.setFixedSize(26, 26)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setStyleSheet(_nav_style())
        self.prev_btn.clicked.connect(self.show_previous)
        row.addWidget(self.prev_btn)

        self.image = QLabel()
        self.image.setFixedHeight(_IMAGE_HEIGHT)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setStyleSheet(
            f"background: rgba(255,255,255,0.03);"
            f" border: 1px solid {Colors.BORDER}; border-radius: 8px;"
            f" color: {Colors.TEXT_3}; font-size: {Fonts.SM};")
        row.addWidget(self.image, 1)

        self.next_btn = QPushButton("›")
        self.next_btn.setFixedSize(26, 26)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setStyleSheet(_nav_style())
        self.next_btn.clicked.connect(self.show_next)
        row.addWidget(self.next_btn)

        root.addLayout(row)

        footer = QHBoxLayout()
        footer.setContentsMargins(2, 0, 2, 0)
        footer.setSpacing(6)
        self.caption_label = QLabel()
        self.caption_label.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM};"
            " background: transparent;")
        self.caption_label.setWordWrap(True)
        footer.addWidget(self.caption_label, 1)
        self.counter_label = QLabel()
        self.counter_label.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
            " background: transparent;")
        footer.addWidget(self.counter_label, 0)
        root.addLayout(footer)

        self.prev_btn.setVisible(False)
        self.next_btn.setVisible(False)
        self.slides_ready.connect(self.set_slides)

    @property
    def count(self):
        return len(self._slides)

    @property
    def current_index(self):
        return self._index

    def load(self, app_id: str):
        """Fetch and display the screenshots of a Flathub app."""
        self._request_id += 1
        request_id = self._request_id
        self._slides = []
        self._index = 0
        self._show_placeholder(_("Loading screenshots…"))
        self.loaded.emit(0)
        threading.Thread(
            target=self._fetch, args=(app_id, request_id),
            daemon=True).start()

    def _fetch(self, app_id: str, request_id: int):
        slides = []
        try:
            for item in self._fetcher(app_id)[:_MAX_SLIDES]:
                data = item.get("data")
                if data is None and item.get("url"):
                    data = _download(item["url"])
                if data:
                    slides.append({
                        "caption": item.get("caption") or "",
                        "data": data,
                    })
        except Exception:
            slides = []
        try:
            self.slides_ready.emit(request_id, slides)
        except RuntimeError:
            pass

    def clear(self):
        self._request_id += 1
        self._slides = []
        self._index = 0
        self.image.clear()
        self.image.setText("")
        self.caption_label.clear()
        self.counter_label.clear()
        self.prev_btn.setVisible(False)
        self.next_btn.setVisible(False)

    def set_slides(self, request_id: int, slides: list):
        if request_id != self._request_id:
            return
        pixmaps = []
        for slide in slides:
            pixmap = slide.get("pixmap")
            if pixmap is None:
                data = slide.get("data")
                pixmap = QPixmap()
                if data:
                    pixmap.loadFromData(data)
            if pixmap is not None and not pixmap.isNull():
                pixmaps.append({
                    "caption": slide.get("caption") or "",
                    "pixmap": pixmap,
                })
        self._slides = pixmaps
        self._index = 0
        if not self._slides:
            self._show_placeholder(_("No screenshots available."))
            self.loaded.emit(0)
            return
        self._render()
        self.loaded.emit(len(self._slides))

    def _show_placeholder(self, text: str):
        self.image.clear()
        self.image.setText(text)
        self.caption_label.clear()
        self.counter_label.clear()
        self.prev_btn.setVisible(False)
        self.next_btn.setVisible(False)

    def _render(self):
        slide = self._slides[self._index]
        pixmap = slide["pixmap"]
        target = self.image.size()
        if target.width() <= 0:
            target.setWidth(260)
        scaled = pixmap.scaled(
            target, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.image.setPixmap(scaled)
        self.caption_label.setText(slide["caption"])
        many = len(self._slides) > 1
        self.counter_label.setText(
            f"{self._index + 1} / {len(self._slides)}" if many else "")
        self.prev_btn.setVisible(many)
        self.next_btn.setVisible(many)
        self.prev_btn.setEnabled(self._index > 0)
        self.next_btn.setEnabled(self._index < len(self._slides) - 1)

    def show_previous(self):
        if self._index > 0:
            self._index -= 1
            self._render()

    def show_next(self):
        if self._index < len(self._slides) - 1:
            self._index += 1
            self._render()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._slides:
            self._render()
