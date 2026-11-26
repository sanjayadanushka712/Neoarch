"""System tray icon with an update-count badge.

The tray mirrors pamac's behaviour: the app keeps a tray icon alive while
it runs, overlays the number of pending updates on it, and exposes quick
actions (open, check for updates, quit) from a context menu.
"""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QCursor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from neoarch.backend.services.i18n import _
from neoarch.frontend.tokens import Colors, Radii, qcolor

__all__ = ["badge_pixmap", "TrayIcon", "tray_available"]

_ICON_SIZE = 64
_BADGE_DIAMETER = 28


def badge_pixmap(base, count):
    """Return `base` with an update-count badge painted in the corner."""
    canvas = QPixmap(_ICON_SIZE, _ICON_SIZE)
    canvas.fill(Qt.GlobalColor.transparent)
    if base is None or base.isNull():
        base = QPixmap(_ICON_SIZE, _ICON_SIZE)
        base.fill(Qt.GlobalColor.transparent)
    scaled = base.scaled(
        _ICON_SIZE, _ICON_SIZE,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap(
        (_ICON_SIZE - scaled.width()) // 2,
        (_ICON_SIZE - scaled.height()) // 2,
        scaled)
    try:
        count = max(0, int(count))
    except (TypeError, ValueError):
        count = 0
    if count <= 0:
        painter.end()
        return canvas

    rect = QRectF(
        _ICON_SIZE - _BADGE_DIAMETER - 1,
        _ICON_SIZE - _BADGE_DIAMETER - 1,
        _BADGE_DIAMETER, _BADGE_DIAMETER)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(qcolor(Colors.RED))
    painter.drawEllipse(rect)

    text = "99+" if count > 99 else str(count)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(15 if len(text) < 3 else 11)
    painter.setFont(font)
    painter.setPen(qcolor(Colors.WHITE))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return canvas


def tray_available():
    """True when the current desktop exposes a system tray."""
    try:
        return bool(QSystemTrayIcon.isSystemTrayAvailable())
    except Exception:
        return False


class TrayIcon(QSystemTrayIcon):
    """Tray icon wired to the main window with an update badge."""

    def __init__(self, app, icon_path, parent=None):
        super().__init__(parent)
        self._app = app
        self._base = QIcon(icon_path).pixmap(_ICON_SIZE, _ICON_SIZE)
        self._count = 0
        self.setIcon(QIcon(badge_pixmap(self._base, 0)))
        self.setToolTip("NeoArch")

        self.menu = QMenu(parent)
        self.menu.setStyleSheet(self._menu_qss())
        self.open_action = self.menu.addAction(_("Open NeoArch"))
        self.open_action.triggered.connect(self.show_window)
        self.check_action = self.menu.addAction(_("Check for Updates"))
        self.check_action.triggered.connect(self.check_updates)
        self.menu.addSeparator()
        self.quit_action = self.menu.addAction(_("Quit NeoArch"))
        self.quit_action.triggered.connect(self.quit_app)
        self.menu.aboutToShow.connect(self.refresh_theme)
        self.setContextMenu(self.menu)
        self.activated.connect(self._on_activated)

    @staticmethod
    def _menu_qss():
        return f"""
            QMenu {{
                background-color: {Colors.GLASS_3_95};
                color: {Colors.TEXT};
                border: 1px solid {Colors.ACCENT_BORDER_STRONG};
                border-radius: {Radii.MD}px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 18px;
                border-radius: 6px;
                background: transparent;
            }}
            QMenu::item:selected {{
                background-color: {Colors.ACCENT_SOFT};
                color: {Colors.ACCENT_HOVER};
            }}
            QMenu::separator {{
                height: 1px;
                background: {Colors.BORDER};
                margin: 5px 8px;
            }}
        """

    def refresh_theme(self):
        """Reapply the tray menu colors after a theme change."""
        self.menu.setStyleSheet(self._menu_qss())

    def update_count(self):
        return self._count

    def set_base_icon(self, icon_path):
        """Swap the underlying brand icon while preserving the badge."""
        self._base = QIcon(icon_path).pixmap(_ICON_SIZE, _ICON_SIZE)
        self.set_update_count(self._count)

    def set_update_count(self, count):
        try:
            count = max(0, int(count))
        except (TypeError, ValueError):
            count = 0
        self._count = count
        self.setIcon(QIcon(badge_pixmap(self._base, count)))
        if count <= 0:
            self.setToolTip("NeoArch")
        else:
            self.setToolTip(
                _("NeoArch — {n} update(s) available").format(n=count))

    def show_window(self):
        try:
            self._app.showNormal()
            self._app.raise_()
            self._app.activateWindow()
        except Exception:
            pass

    def check_updates(self):
        self.show_window()
        try:
            self._app._handle_nav("updates")
        except Exception:
            try:
                self._app.switch_view("updates")
            except Exception:
                pass

    def quit_app(self):
        try:
            from neoarch.backend.session_auth import cleanup_session
            cleanup_session()
        except Exception:
            pass
        request_quit = getattr(self._app, 'request_quit', None)
        if request_quit is not None:
            request_quit()
            return
        self.hide()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def show_menu(self):
        """Show an app-rendered menu so theme colors are not lost to the desktop shell."""
        if self.menu.isVisible():
            return
        self.refresh_theme()
        self.menu.popup(QCursor.pos())

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Some Linux trays render the native context menu with the desktop
            # accent.  Left-click keeps a themed, app-rendered menu available.
            self.show_menu()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()
