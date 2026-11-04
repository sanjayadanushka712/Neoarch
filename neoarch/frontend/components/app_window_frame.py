"""Window frame that can paint a theme-owned wallpaper behind the UI."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
)

from neoarch.frontend import tokens
from neoarch.frontend.tokens import Colors, qcolor

__all__ = ["AppWindowFrame"]


def _blur_pixmap(source: QPixmap, radius: int) -> QPixmap:
    if source.isNull() or radius <= 0:
        return source
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(source)
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(float(radius))
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    scene.setSceneRect(QRectF(source.rect()))
    image = QImage(source.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        scene.render(
            painter,
            QRectF(image.rect()),
            QRectF(source.rect()),
        )
    finally:
        painter.end()
        scene.clear()
    return QPixmap.fromImage(image)


def _cover_pixmap(
    source: QPixmap,
    width: int,
    height: int,
    dpr: float,
    position: str,
) -> QPixmap:
    target_width = max(1, int(round(width * dpr)))
    target_height = max(1, int(round(height * dpr)))
    scaled = source.scaled(
        target_width,
        target_height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    extra_x = max(0, scaled.width() - target_width)
    extra_y = max(0, scaled.height() - target_height)
    if "left" in position:
        x = 0
    elif "right" in position:
        x = extra_x
    else:
        x = extra_x // 2
    if "top" in position:
        y = 0
    elif "bottom" in position:
        y = extra_y
    else:
        y = extra_y // 2
    result = scaled.copy(x, y, target_width, target_height)
    result.setDevicePixelRatio(dpr)
    return result


class AppWindowFrame(QFrame):
    """QFrame that paints an optional blurred wallpaper behind its children."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._background: dict | None = None
        self._source: QPixmap | None = None
        self._blurred: QPixmap | None = None
        self._cover_cache: QPixmap | None = None
        self._cover_key = None

    def set_theme_background(self, background: dict | None) -> None:
        value = dict(background) if isinstance(background, dict) else None
        if value == self._background:
            return
        self._background = value
        self._source = None
        self._blurred = None
        self._cover_cache = None
        self._cover_key = None
        if value and value.get("mode", "image") == "image":
            image = str(value.get("image") or "")
            pixmap = QPixmap(image) if image else QPixmap()
            if not pixmap.isNull():
                self._source = pixmap
                try:
                    blur = int(value.get("blur") or 0)
                except (TypeError, ValueError):
                    blur = 0
                if blur > 0:
                    self._blurred = _blur_pixmap(pixmap, blur)
        self.update()

    def _paintable(self) -> QPixmap | None:
        return self._blurred or self._source

    def _repaint_cache(self, width: int, height: int, margin: int) -> QPixmap | None:
        source = self._paintable()
        if source is None:
            return None
        dpr = self.devicePixelRatioF()
        position = str((self._background or {}).get("position") or "center")
        key = (width, height, dpr, id(source), position, margin)
        if key != self._cover_key:
            self._cover_cache = _cover_pixmap(
                source,
                width + margin * 2,
                height + margin * 2,
                dpr,
                position,
            )
            self._cover_key = key
        return self._cover_cache

    def paintEvent(self, event):
        super().paintEvent(event)
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return
        radius = int(tokens.WINDOW_RADIUS)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setClipPath(path)
        source = self._paintable()
        if source is not None:
            try:
                blur = int((self._background or {}).get("blur") or 0)
            except (TypeError, ValueError):
                blur = 0
            margin = max(4, blur * 2)
            cover = self._repaint_cache(width, height, margin)
            if cover is not None:
                try:
                    opacity = float((self._background or {}).get("opacity", 1.0))
                except (TypeError, ValueError):
                    opacity = 1.0
                try:
                    window_opacity = float(tokens.WINDOW_OPACITY)
                except (TypeError, ValueError):
                    window_opacity = 1.0
                opacity = (
                    max(0.0, min(1.0, opacity))
                    * max(0.0, min(1.0, window_opacity))
                )
                painter.setOpacity(opacity)
                painter.drawPixmap(-margin, -margin, cover)
                scrim = str((self._background or {}).get("scrim") or "")
                if scrim:
                    painter.fillPath(path, qcolor(scrim))
                painter.setOpacity(1.0)
        else:
            try:
                window_opacity = float(tokens.WINDOW_OPACITY)
            except (TypeError, ValueError):
                window_opacity = 1.0
            window_opacity = max(0.0, min(1.0, window_opacity))
            background = qcolor(Colors.BG)
            background.setAlphaF(background.alphaF() * window_opacity)
            painter.fillPath(path, background)
        painter.setClipping(False)
        if tokens.WINDOW_GLOW:
            color = qcolor(tokens.WINDOW_GLOW_COLOR or Colors.ACCENT_SOFT)
            color.setAlphaF(color.alphaF() * tokens.WINDOW_GLOW_OPACITY)
            width = max(0.5, float(tokens.WINDOW_GLOW_WIDTH))
            inset = rect.adjusted(width / 2, width / 2,
                                  -width / 2, -width / 2)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, width))
            border = QPainterPath()
            border.addRoundedRect(inset, radius, radius)
            painter.drawPath(border)
        painter.end()
