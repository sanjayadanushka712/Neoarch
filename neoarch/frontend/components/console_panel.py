"""Resizable console panel for NeoArch.

The console is the bottom strip of the main window that streams pacman,
AUR and service output. It used to be pinned to a fixed 150 px, which made
long logs unreadable. This module provides the pieces that let the user
grow it:

* :class:`ConsoleTextEdit` — a ``QTextEdit`` whose *size hint* follows the
  requested height, so the surrounding layout honours that height instead
  of the default text-edit hint (which would otherwise leave a gap).
* :class:`ResizeGrip` — a thin handle the user drags to resize the strip.
  The drag is measured against the global cursor position so the handle
  never drifts away from the pointer while the layout reflows.
* :class:`ConsolePanel` — grip + header (title and actions) + log view.

The panel keeps the log view as a *child* of itself and proxies the
handful of ``QTextEdit`` methods the rest of the app calls, so the main
window can keep treating ``self.console`` as a single widget.
"""

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget,
)

from neoarch.backend.services.i18n import _
from neoarch.frontend.icon_registry import icon_path
from neoarch.frontend.tokens import Colors, Radii

__all__ = [
    "ConsolePanel",
    "ConsoleTextEdit",
    "ResizeGrip",
    "CONSOLE_MIN_HEIGHT",
    "CONSOLE_DEFAULT_HEIGHT",
]

# Smallest usable strip (the log stays readable below this).
CONSOLE_MIN_HEIGHT = 90
# Height the console starts at when nothing was persisted yet.
CONSOLE_DEFAULT_HEIGHT = 150
# Upper bound for a manual drag — the layout shrinks it further if the
# window itself is too short to honour the request.
CONSOLE_MAX_HEIGHT = 4000
# Size the console asks for while it is expanded. The host layout usually
# hands it more room than this; the hint only keeps the strip from
# collapsing when it is the only widget with space to share.
CONSOLE_EXPANDED_SIZE_HINT = 400


class ConsoleTextEdit(QTextEdit):
    """Read-only log view whose preferred height is user-controlled.

    ``QTextEdit`` reports a fairly large default size hint, so a plain
    text edit pinned with ``setFixedHeight`` leaves a gap in the layout.
    Overriding the hint keeps the widget exactly as tall as requested.
    """

    def __init__(self, parent=None, height=CONSOLE_DEFAULT_HEIGHT):
        super().__init__(parent)
        self._target_height = max(CONSOLE_MIN_HEIGHT, int(height))
        self._expanded = False
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_constraints()

    # ── height control ──────────────────────────────────────────────

    @property
    def target_height(self) -> int:
        """Resting height of the strip in pixels."""
        return self._target_height

    @property
    def expanded(self) -> bool:
        return self._expanded

    def _apply_constraints(self):
        """Push the current target/expanded state onto the widget."""
        if self._expanded:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Expanding)
        else:
            self.setMinimumHeight(min(CONSOLE_MIN_HEIGHT, self._target_height))
            self.setMaximumHeight(self._target_height)
            self.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Fixed)
        self.updateGeometry()

    def set_height(self, height: int):
        """Set the resting height of the strip (clamped to sane bounds)."""
        height = max(CONSOLE_MIN_HEIGHT, min(int(height), CONSOLE_MAX_HEIGHT))
        self._target_height = height
        if not self._expanded:
            self._apply_constraints()

    def set_expanded(self, expanded: bool):
        """Let the strip fill the available space, or return to its height."""
        expanded = bool(expanded)
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self._apply_constraints()

    # ── size hints ──────────────────────────────────────────────────

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        if self._expanded:
            height = max(self._target_height, CONSOLE_EXPANDED_SIZE_HINT)
        else:
            height = self._target_height
        return QSize(hint.width(), height)

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        if self._expanded:
            height = 0
        else:
            height = min(self._target_height, CONSOLE_MIN_HEIGHT)
        return QSize(hint.width(), height)


class ResizeGrip(QWidget):
    """Thin horizontal handle the user drags to resize the console.

    The drag is measured from the global cursor position captured on
    press, so the handle stays under the pointer even when the layout
    reflows (and even when the requested height gets clamped).
    """

    resizeRequested = pyqtSignal(int)  # requested console height in px

    def __init__(self, parent=None, height_provider=None):
        super().__init__(parent)
        self._height_provider = height_provider
        self._start_global_y = 0.0
        self._start_height = 0
        self._active = False
        self.setFixedHeight(8)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setToolTip(_("Drag to resize the console"))

    def set_height_provider(self, provider):
        """Register the callable returning the console's current height."""
        self._height_provider = provider

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._active = True
        self._start_global_y = event.globalPosition().y()
        self._start_height = 0
        if callable(self._height_provider):
            try:
                self._start_height = int(self._height_provider())
            except Exception:
                self._start_height = CONSOLE_DEFAULT_HEIGHT
        event.accept()

    def mouseMoveEvent(self, event):
        if not self._active:
            super().mouseMoveEvent(event)
            return
        delta = int(event.globalPosition().y() - self._start_global_y)
        self.resizeRequested.emit(self._start_height - delta)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._active = False
        super().mouseReleaseEvent(event)


class ConsolePanel(QWidget):
    """Grip, header actions and log view for the console strip."""

    heightChanged = pyqtSignal(int)      # resting height in px
    expandedChanged = pyqtSignal(bool)    # strip took over the panel
    wrapChanged = pyqtSignal(bool)        # soft-wrap state
    statusMessage = pyqtSignal(str)       # user-facing feedback string

    def __init__(self, parent=None, icon_provider=None, title=None):
        super().__init__(parent)
        self._icon_provider = icon_provider
        self._expanded = False
        self._wrap = True
        self._build_ui(_("Console Output") if title is None else title)

    # ── construction ────────────────────────────────────────────────

    def _icon(self, name, size=16):
        """Load an icon from the shared ui icon folder (best effort)."""
        if not callable(self._icon_provider):
            return None
        try:
            return self._icon_provider(icon_path(f"ui/{name}"), size)
        except Exception:
            return None

    def _button(self, tooltip, icon_name, on_click):
        btn = QPushButton()
        btn.setFixedSize(26, 26)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFlat(True)
        icon = self._icon(icon_name)
        if icon is not None:
            btn.setIcon(icon)
            btn.setIconSize(QSize(16, 16))
        btn.clicked.connect(on_click)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: {Radii.MD}px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {Colors.ACCENT_SOFT};
                border-color: {Colors.ACCENT_BORDER};
            }}
            QPushButton:pressed {{
                background: {Colors.ACCENT_20};
            }}
        """)
        return btn

    def _build_ui(self, title):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.grip = ResizeGrip(self)
        self.grip.set_height_provider(lambda: self.console.target_height)
        self.grip.resizeRequested.connect(self._on_resize_requested)
        outer.addWidget(self.grip, 0)

        # Header row: title on the left, actions on the right.
        self.header = QWidget()
        self.header.setObjectName("consoleHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(2, 0, 2, 0)
        header_layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionLabel")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)

        self.expand_btn = self._button(_("Expand console"), "chevron_up.svg",
                                       self.toggle_expanded)
        header_layout.addWidget(self.expand_btn)

        self.wrap_btn = self._button(_("Wrap long lines"), "wrap.svg",
                                     self._on_wrap_clicked)
        header_layout.addWidget(self.wrap_btn)

        self.copy_btn = self._button(_("Copy console output"), "copy.svg",
                                     self.copy_all)
        header_layout.addWidget(self.copy_btn)

        self.clear_btn = self._button(_("Clear console"), "clear.svg",
                                      self.clear)
        header_layout.addWidget(self.clear_btn)

        outer.addWidget(self.header, 0)

        self.console = ConsoleTextEdit(self)
        try:
            self.console.document().setMaximumBlockCount(500)
        except Exception:
            pass
        outer.addWidget(self.console, 1)

        self.set_wrap(self._wrap)

        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)

    # ── console API (proxied to the log view) ───────────────────────

    def append(self, text):
        """Append a line of output to the log view."""
        self.console.append(text)

    def clear(self):
        """Remove every line from the log view."""
        self.console.clear()

    def textCursor(self):
        return self.console.textCursor()

    def document(self):
        return self.console.document()

    def toPlainText(self):
        return self.console.toPlainText()

    def copy_all(self):
        """Copy the whole log to the clipboard."""
        text = self.console.toPlainText()
        if not text.strip():
            self.statusMessage.emit(_("Nothing to copy"))
            return
        try:
            QApplication.clipboard().setText(text)
            self.statusMessage.emit(_("Console output copied"))
        except Exception:
            self.statusMessage.emit(_("Could not copy the console output"))

    # ── sizing ──────────────────────────────────────────────────────

    @property
    def expanded(self) -> bool:
        return self._expanded

    @property
    def wrap(self) -> bool:
        return self._wrap

    def set_height(self, height):
        """Set the resting height of the console strip."""
        self.console.set_height(height)
        self._relayout()
        self.heightChanged.emit(self.console.target_height)

    def height(self):
        """The resting height of the console strip in pixels."""
        return self.console.target_height

    def set_expanded(self, expanded):
        """Expand the console to fill the panel, or restore it."""
        expanded = bool(expanded)
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self.console.set_expanded(expanded)
        if expanded:
            self.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Expanding)
            self.expand_btn.setToolTip(_("Collapse console"))
            icon = self._icon("chevron_down.svg")
            if icon is not None:
                self.expand_btn.setIcon(icon)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Fixed)
            self.expand_btn.setToolTip(_("Expand console"))
            icon = self._icon("chevron_up.svg")
            if icon is not None:
                self.expand_btn.setIcon(icon)
        self._relayout()
        self.expandedChanged.emit(expanded)

    def toggle_expanded(self):
        self.set_expanded(not self._expanded)

    def _relayout(self):
        """Re-run the layout so the new height is picked up."""
        try:
            self.console.updateGeometry()
            if self.layout() is not None:
                self.layout().invalidate()
            self.updateGeometry()
            parent = self.parentWidget()
            if parent is not None and parent.layout() is not None:
                parent.layout().invalidate()
        except Exception:
            pass

    def _on_resize_requested(self, height):
        """Handle a drag on the grip."""
        if self._expanded:
            return
        self.set_height(height)

    # ── header actions ──────────────────────────────────────────────

    def _on_wrap_clicked(self):
        self.set_wrap(not self._wrap)

    def set_wrap(self, wrap):
        """Toggle soft wrapping of long log lines."""
        wrap = bool(wrap)
        changed = wrap != self._wrap
        self._wrap = wrap
        try:
            if self._wrap:
                self.console.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            else:
                self.console.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        except Exception:
            pass
        try:
            self.wrap_btn.setToolTip(
                _("Disable line wrap") if self._wrap else _("Wrap long lines"))
            icon = self._icon("nowrap.svg" if self._wrap else "wrap.svg")
            if icon is not None:
                self.wrap_btn.setIcon(icon)
        except Exception:
            pass
        if changed:
            self.wrapChanged.emit(self._wrap)
