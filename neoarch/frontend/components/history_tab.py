"""Package history full-page view for NeoArch.

Lists pacman transactions (installs, upgrades, downgrades, reinstalls and
removals) parsed from /var/log/pacman.log, newest first, in the same table
design as the Updates page: frosted header, dense rows, hover band, hairlines
and stacked version changes.

The log is read off the UI thread and only its tail is parsed, so the page
opens instantly. While it loads the Updates page loading state is shown.
"""

import os
import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTableView, QHeaderView, QStyledItemDelegate,
    QAbstractItemView, QProgressBar,
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QAbstractTableModel, QModelIndex, QRect, QRectF, QSize,
    QPointF,
)
from PyQt6.QtGui import (
    QColor, QFont, QFontMetrics, QIcon, QLinearGradient, QPainter,
    QPainterPath, QPen, QRadialGradient,
)

from neoarch.frontend.tokens import Colors, Fonts, Radii
from neoarch.frontend.styles import Styles
from neoarch.backend.services.i18n import _
from neoarch.backend.services.history import read_history, history_stats
from neoarch.resources.paths import PROJECT_ROOT

__all__ = ["HistoryTab"]

# ── theme, mirrored from the Updates table ──────────────────────────
_ACCENT = QColor(Colors.ACCENT)
_TEXT = QColor(Colors.TEXT)
_TEXT_SEC = QColor(Colors.TEXT_2)
_TEXT_MUTED = QColor(Colors.TEXT_3)
_GREEN = QColor(88, 202, 143)
_YELLOW = QColor(Colors.YELLOW)

_ROW_HOVER = QColor(255, 255, 255, 22)
_SEPARATOR = QColor(255, 255, 255, 16)
_HEADER_TEXT = QColor(139, 141, 151)
_HEADER_BORDER = QColor(255, 255, 255, 15)
_PANEL_RADIUS = 14

_VIEWPORT_GLASS = """
QWidget {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0    rgba(22, 23, 26, 150),
        stop:0.06 rgba(20, 21, 24, 165),
        stop:0.6  rgba(16, 17, 20, 180),
        stop:1    rgba(12, 12, 14, 190));
    border: none;
}
"""

_HEADERS = ("Time", "Package", "Version", "Date")

_ACTION_COLORS = {
    "install": QColor(Colors.GREEN),
    "upgrade": QColor(Colors.ACCENT),
    "downgrade": QColor(Colors.YELLOW),
    "reinstall": QColor(Colors.BLUE),
    "remove": QColor(Colors.RED),
}

_ACTION_LABELS = {
    "install": "Installed",
    "upgrade": "Upgraded",
    "downgrade": "Downgraded",
    "reinstall": "Reinstalled",
    "remove": "Removed",
}


class _HistoryModel(QAbstractTableModel):
    """Flat rows, one per package event (newest first)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(_HEADERS)

    def row_at(self, row):
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None


class _HistoryHeader(QHeaderView):
    """Frosted sticky header, matching the Updates table."""

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSectionsClickable(False)
        self.setHighlightSections(False)
        self.setMinimumHeight(44)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._font = QFont()
        self._font.setPointSize(9)
        self._font.setWeight(QFont.Weight.DemiBold)
        self._font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
        self._section_rects = []
        self.sectionResized.connect(self._refresh_section_rects)
        self.sectionMoved.connect(self._refresh_section_rects)
        self.sectionCountChanged.connect(self._refresh_section_rects)

    def _refresh_section_rects(self, *args):
        try:
            self._section_rects = [
                QRect(self.sectionViewportPosition(s), 0, self.sectionSize(s), self.height())
                for s in range(self.count())]
        except Exception:
            self._section_rects = []

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_section_rects()

    def paintSection(self, painter, rect, section):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        label = _(_HEADERS[section]).upper() if 0 <= section < len(_HEADERS) else ""

        if 0 <= section < len(self._section_rects):
            rect = self._section_rects[section]

        glass = QLinearGradient(0, rect.top(), 0, rect.bottom())
        glass.setColorAt(0.0, QColor(19, 20, 23, 200))
        glass.setColorAt(1.0, QColor(12, 12, 14, 215))
        is_first = section == 0
        is_last = section == self.count() - 1
        if is_first or is_last:
            path = QPainterPath()
            r = QRectF(rect)
            rad = _PANEL_RADIUS
            if is_first and is_last:
                path.addRoundedRect(r, rad, rad)
            elif is_first:
                path.moveTo(r.right(), r.top())
                path.lineTo(r.right(), r.bottom())
                path.lineTo(r.left(), r.bottom())
                path.lineTo(r.left(), r.top() + rad)
                path.quadTo(r.left(), r.top(), r.left() + rad, r.top())
            else:
                path.moveTo(r.left(), r.bottom())
                path.lineTo(r.left(), r.top() + rad)
                path.quadTo(r.left(), r.top(), r.left() + rad, r.top())
                path.lineTo(r.right() - rad, r.top())
                path.quadTo(r.right(), r.top(), r.right(), r.top() + rad)
                path.lineTo(r.right(), r.bottom())
            path.closeSubpath()
            painter.fillPath(path, glass)
        else:
            painter.fillRect(QRectF(rect), glass)

        text_rect = QRectF(rect)
        text_rect.setLeft(rect.left() + (12 if section == 1 else 6))
        painter.setFont(self._font)
        painter.setPen(_HEADER_TEXT)
        painter.drawText(text_rect,
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                         | Qt.TextFlag.TextSingleLine, label)

        line_pen = QPen(_HEADER_BORDER)
        line_pen.setWidthF(1)
        painter.setPen(line_pen)
        painter.drawLine(int(rect.left()), int(rect.bottom()) - 1,
                         int(rect.right()), int(rect.bottom()) - 1)
        painter.restore()


class _HistoryDelegate(QStyledItemDelegate):
    """Paints history rows like the Updates table rows."""

    def __init__(self, table):
        super().__init__(table)
        self._table = table
        self._name_font = QFont()
        self._name_font.setPointSize(10)
        self._name_font.setWeight(QFont.Weight.DemiBold)
        self._desc_font = QFont()
        self._desc_font.setPointSize(8)
        self._ver_font = QFont()
        self._ver_font.setPointSize(9)

    @staticmethod
    def sizeHint(option, index):
        return QSize(0, 52)

    def _row_rect(self, option):
        table = self._table
        try:
            left = table.columnViewportPosition(0)
            right = (table.columnViewportPosition(table.columnCount() - 1)
                     + table.columnWidth(table.columnCount() - 1))
        except Exception:
            return QRectF(option.rect)
        top = option.rect.top()
        height = max(option.rect.height(), table.verticalHeader().sectionSize(0))
        return QRectF(left, top, max(1, right - left), height)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        rect = QRectF(option.rect)
        row = index.row()
        row_item = self._table.model.row_at(row)
        self._paint_row_background(painter, self._row_rect(option), row)
        if row_item is None:
            painter.restore()
            return

        painter.save()
        painter.setClipRect(rect)
        col = index.column()
        if col == 0:
            self._paint_time(painter, rect, row_item)
        elif col == 1:
            self._paint_package(painter, rect, row_item)
        elif col == 2:
            self._paint_version(painter, rect, row_item)
        elif col == 3:
            self._paint_date(painter, rect, row_item)
        painter.restore()
        painter.restore()

    def _paint_row_background(self, painter, rect, row):
        if row == self._table.hovered_row():
            band = QRectF(rect.left() + 2, rect.top() + 1, rect.width() - 4, rect.height() - 2)
            path = QPainterPath()
            path.addRoundedRect(band, 6, 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(path, _ROW_HOVER)

        pen = QPen(_SEPARATOR)
        pen.setWidthF(1)
        painter.setPen(pen)
        painter.drawLine(QPointF(rect.left() + 14, rect.bottom()),
                         QPointF(rect.right() - 14, rect.bottom()))

    def _paint_time(self, painter, rect, row_item):
        ts = row_item.get("timestamp")
        text = ts.strftime("%H:%M") if ts else "—"
        painter.setFont(self._ver_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(rect.left() + 14, rect.top(), rect.width() - 14, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                         | Qt.TextFlag.TextSingleLine, text)

    def _paint_package(self, painter, rect, row_item):
        text_left = rect.left() + 12
        avail_w = max(20, rect.right() - text_left - 4)

        name = row_item.get("name") or ""
        name_fm = QFontMetrics(self._name_font)
        name_el = name_fm.elidedText(name, Qt.TextElideMode.ElideRight, int(avail_w))
        painter.setFont(self._name_font)
        painter.setPen(_TEXT)
        painter.drawText(QRectF(text_left, rect.top() + 7, avail_w, 16),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                         | Qt.TextFlag.TextSingleLine, name_el)

        action = row_item.get("action", "")
        color = _ACTION_COLORS.get(action, _TEXT_SEC)
        label = _(_ACTION_LABELS.get(action, action))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(text_left + 3, rect.top() + 33), 3, 3)
        painter.setFont(self._desc_font)
        painter.setPen(color)
        painter.drawText(QRectF(text_left + 11, rect.top() + 26, max(10, avail_w - 11), 15),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                         | Qt.TextFlag.TextSingleLine,
                         QFontMetrics(self._desc_font).elidedText(
                             label, Qt.TextElideMode.ElideRight, int(max(10, avail_w - 11))))

    def _paint_version(self, painter, rect, row_item):
        old = row_item.get("old_version") or ""
        new = row_item.get("version") or ""
        action = row_item.get("action", "")
        fm = QFontMetrics(self._ver_font)
        cell_left = rect.left() + 6
        cell_w = max(20, rect.width() - 12)
        line_h = 15

        if not old or old == new:
            painter.setFont(self._ver_font)
            painter.setPen(_TEXT_SEC)
            painter.drawText(QRectF(cell_left, rect.top(), cell_w, rect.height()),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                             | Qt.TextFlag.TextSingleLine,
                             fm.elidedText(new or old or "—",
                                           Qt.TextElideMode.ElideMiddle, int(cell_w)))
            return

        color = _YELLOW if action == "downgrade" else _GREEN
        arrow = "\u2193" if action == "downgrade" else "\u2191"

        painter.setFont(self._ver_font)
        painter.setPen(_TEXT_MUTED)
        painter.drawText(QRectF(cell_left, rect.top() + 6, cell_w, line_h),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                         | Qt.TextFlag.TextSingleLine,
                         fm.elidedText(old, Qt.TextElideMode.ElideMiddle, int(cell_w)))

        new_el = fm.elidedText(new, Qt.TextElideMode.ElideMiddle, int(max(10, cell_w - 14)))
        new_top = rect.top() + 27
        painter.setPen(QPen(color, 1.6))
        painter.drawText(QRectF(cell_left, new_top, 12, line_h),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                         | Qt.TextFlag.TextSingleLine, arrow)
        painter.setPen(color)
        painter.drawText(QRectF(cell_left + 12, new_top, max(10, cell_w - 12), line_h),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                         | Qt.TextFlag.TextSingleLine, new_el)

    def _paint_date(self, painter, rect, row_item):
        ts = row_item.get("timestamp")
        text = ts.strftime("%b %d, %Y") if ts else "—"
        fm = QFontMetrics(self._ver_font)
        el = fm.elidedText(text, Qt.TextElideMode.ElideLeft, int(max(12, rect.width() - 10)))
        painter.setFont(self._ver_font)
        painter.setPen(_TEXT_SEC)
        painter.drawText(QRectF(rect.left() + 4, rect.top(), rect.width() - 10, rect.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                         | Qt.TextFlag.TextSingleLine, el)


class _HistoryTable(QTableView):
    """Table with hover tracking, matching the Updates table shell."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("updatesTable")
        self._hover_row = -1
        self.overlay = None
        self.model = _HistoryModel(self)
        self.setModel(self.model)
        self.setItemDelegate(_HistoryDelegate(self))
        self.setShowGrid(False)
        self.setFrameShape(QTableView.Shape.NoFrame)
        self.viewport().setAutoFillBackground(True)
        self.viewport().setStyleSheet(_VIEWPORT_GLASS)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(52)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        header = _HistoryHeader(self)
        self.setHorizontalHeader(header)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in (0, 2, 3):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 84)
        self.setColumnWidth(2, 176)
        self.setColumnWidth(3, 110)

        self.setStyleSheet(Styles.scrollbar())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.overlay is not None:
            self.overlay.setGeometry(self.rect())

    def hovered_row(self):
        return self._hover_row

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        row = self.indexAt(pos).row()
        if row != self._hover_row:
            self._hover_row = row
            self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_row != -1:
            self._hover_row = -1
            self.viewport().update()
        super().leaveEvent(event)


class _FilterChip(QPushButton):
    """Segmented-control filter chip, matching the Docker tab."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)
        self.toggled.connect(self._apply_style)

    def _apply_style(self, checked):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(0, 191, 174, 0.14);
                    color: {Colors.ACCENT};
                    border: 1px solid rgba(0, 191, 174, 0.25);
                    border-radius: 10px;
                    padding: 0 16px;
                    font-size: {Fonts.MD}; font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {Colors.TEXT_2};
                    border: 1px solid transparent;
                    border-radius: 10px;
                    padding: 0 16px;
                    font-size: {Fonts.MD}; font-weight: 500;
                }}
                QPushButton:hover {{
                    color: {Colors.TEXT};
                    background: rgba(255, 255, 255, 0.04);
                }}
            """)


class _StatCard(QFrame):
    """Compact overview stat card, matching the Git/AppImage tabs."""

    def __init__(self, title, value, subtitle, color, parent=None):
        super().__init__(parent)
        self.setObjectName("historyStatCard")
        self.setFixedHeight(88)
        self.setStyleSheet(f"""
            QFrame#historyStatCard {{
                background: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radii.XL}px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM}; font-weight: 500;"
            "background: transparent; border: none;")
        layout.addWidget(self._title_lbl)

        self._value_lbl = QLabel(str(value))
        self._value_lbl.setStyleSheet(
            f"color: {color}; font-size: {Fonts.DISPLAY}; font-weight: 700;"
            "background: transparent; border: none;")
        layout.addWidget(self._value_lbl)

        self._sub_lbl = QLabel(subtitle)
        self._sub_lbl.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.XS}; font-weight: 400;"
            "background: transparent; border: none;")
        layout.addWidget(self._sub_lbl)


class _Badge(QWidget):
    """Circular mint-glow badge with the history glyph."""

    def __init__(self, size=76, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._size
        cx = cy = s / 2
        r = s / 2 - 4

        glow = QRadialGradient(cx, cy, r)
        glow.setColorAt(0.0, QColor(88, 202, 143, 46))
        glow.setColorAt(0.55, QColor(88, 202, 143, 22))
        glow.setColorAt(1.0, QColor(88, 202, 143, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        p.setPen(QPen(QColor(88, 202, 143, 90), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - r + 2, cy - r + 2, (r - 2) * 2, (r - 2) * 2))

        icon_path = os.path.join(str(PROJECT_ROOT), "assets", "icons", "history.svg")
        if os.path.exists(icon_path):
            pm = QIcon(icon_path).pixmap(30, 30)
            p.drawPixmap(int(cx - 15), int(cy - 15), pm)
        p.end()


class _Overlay(QWidget):
    """Centered loading / empty state shown over the table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch()

        self.badge = _Badge(76)
        layout.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.title = QLabel(_("Loading history…"))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.title.font()
        font.setPointSize(13)
        font.setWeight(QFont.Weight.DemiBold)
        self.title.setFont(font)
        self.title.setStyleSheet("color: #EDEDEF; background: transparent; border: none;")
        layout.addWidget(self.title)

        self.subtitle = QLabel(_("Please wait, reading the pacman log"))
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setStyleSheet("color: #8B8D97; background: transparent; border: none;")
        layout.addWidget(self.subtitle)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(240)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar { border: none; border-radius: 3px;"
            " background: rgba(255,255,255,0.07); }"
            " QProgressBar::chunk { background: #00BFAE; border-radius: 3px; }")
        layout.addSpacing(6)
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

    def set_loading(self):
        self.title.setText(_("Loading history…"))
        self.subtitle.setText(_("Please wait, reading the pacman log"))
        self.progress.setVisible(True)

    def set_empty(self, title, subtitle):
        self.title.setText(title)
        self.subtitle.setText(subtitle)
        self.progress.setVisible(False)


class HistoryTab(QWidget):
    """Full-page package history view."""

    history_loaded = pyqtSignal(list)

    def __init__(self, main_app=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._transactions = []
        self._search_text = ""
        self._action_filter = None
        self._loading = False
        self._init_ui()
        self.history_loaded.connect(self._on_loaded)
        self.refresh()

    # ── UI construction ───────────────────────────────────────────

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 12)
        root.setSpacing(12)

        root.addLayout(self._build_stats())
        root.addLayout(self._build_filters())

        self._list = _HistoryTable(self)
        self._model = self._list.model
        root.addWidget(self._list, 1)

        self._overlay = _Overlay(self._list)
        self._overlay.setVisible(False)
        self._list.overlay = self._overlay
        self._empty_label = self._overlay.title

    def _build_filters(self):
        row = QHBoxLayout()
        row.setSpacing(4)
        row.setContentsMargins(0, 0, 0, 0)
        self._filter_buttons = {}

        entries = [(None, _("All"))]
        for action in ("install", "upgrade", "downgrade", "reinstall", "remove"):
            entries.append((action, _(_ACTION_LABELS[action])))
        for key, label in entries:
            chip = _FilterChip(label)
            chip.clicked.connect(lambda checked, k=key: self._set_action_filter(k))
            self._filter_buttons[key] = chip
            row.addWidget(chip)
        row.addStretch(1)

        self.refresh_btn = QPushButton()
        self.refresh_btn.setFixedSize(30, 30)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setToolTip(_("Refresh"))
        icon_path = os.path.join(str(PROJECT_ROOT), "assets", "icons", "ui", "refresh.svg")
        if os.path.exists(icon_path):
            self.refresh_btn.setIcon(QIcon(icon_path))
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Radii.SM}px;
            }}
            QPushButton:hover {{ border-color: {Colors.ACCENT}; }}
        """)
        self.refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self.refresh_btn)

        self._filter_buttons[None].setChecked(True)
        return row

    def _set_action_filter(self, key):
        self._action_filter = key
        for k, chip in self._filter_buttons.items():
            chip.setChecked(k == key)
        if not self._loading:
            self._render()

    def _build_stats(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)

        self._stat_values = {}
        columns = (
            ("transactions", _("Transactions"), _("From the pacman log"), Colors.ACCENT),
            ("install", _("Installs"), _("Packages installed"), Colors.GREEN),
            ("upgrade", _("Upgrades"), _("Packages upgraded"), Colors.TEAL),
            ("remove", _("Removals"), _("Packages removed"), Colors.RED),
        )
        for key, title, subtitle, color in columns:
            card = _StatCard(title, "0", subtitle, color)
            row.addWidget(card, 1)
            self._stat_values[key] = card._value_lbl
        return row

    # ── data ──────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        if not self._transactions and not self._loading:
            self.refresh()

    def refresh(self):
        if self._loading:
            return
        self._loading = True
        self._show_loading()
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        try:
            transactions = read_history()
        except Exception:
            transactions = []
        try:
            self.history_loaded.emit(transactions)
        except Exception:
            pass

    def _on_loaded(self, transactions):
        self._loading = False
        self._apply(transactions)

    def _apply(self, transactions):
        self._transactions = transactions or []
        stats = history_stats(self._transactions)
        self._stat_values["transactions"].setText(str(stats["transactions"]))
        self._stat_values["install"].setText(str(stats["install"]))
        self._stat_values["upgrade"].setText(
            str(stats["upgrade"] + stats["downgrade"] + stats["reinstall"]))
        self._stat_values["remove"].setText(str(stats["remove"]))
        self._render()

    def set_search_text(self, text):
        """Filter rows from the top navbar search box."""
        self._search_text = (text or "").strip().lower()
        if not self._loading:
            self._render()

    def _visible_transactions(self):
        needle = self._search_text
        action = self._action_filter
        if not needle and action is None:
            return self._transactions
        visible = []
        for transaction in self._transactions:
            packages = []
            for p in transaction["packages"]:
                if action is not None and p["action"] != action:
                    continue
                if needle and not (
                        needle in p["name"].lower()
                        or needle in p["action"].lower()
                        or needle in _ACTION_LABELS.get(p["action"], "").lower()):
                    continue
                packages.append(p)
            if packages:
                visible.append({"timestamp": transaction["timestamp"],
                                "packages": packages})
        return visible

    # ── rendering ─────────────────────────────────────────────────

    def _show_loading(self):
        self._overlay.set_loading()
        self._overlay.setGeometry(self._list.rect())
        self._overlay.raise_()
        self._overlay.setVisible(True)

    def _build_rows(self, transactions):
        rows = []
        for transaction in transactions:
            ts = transaction["timestamp"]
            for package in transaction["packages"]:
                rows.append({
                    "timestamp": ts,
                    "action": package.get("action", ""),
                    "name": package.get("name", ""),
                    "version": package.get("version", ""),
                    "old_version": package.get("old_version", ""),
                })
        return rows

    def _render(self):
        self._overlay.setVisible(False)

        transactions = self._visible_transactions()
        if not transactions:
            self._model.set_rows([])
            if not self._transactions:
                self._overlay.set_empty(
                    _("No history yet."),
                    _("Transactions will appear here after your next pacman operation"))
            else:
                self._overlay.set_empty(
                    _("No matching transactions."),
                    _("Try a different package name or action"))
            self._overlay.setGeometry(self._list.rect())
            self._overlay.raise_()
            self._overlay.setVisible(True)
            return

        self._model.set_rows(self._build_rows(transactions))
        self._list.scrollToTop()
