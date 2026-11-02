# cSpell:disable
"""
Main window module for NeoArch Package Manager
"""

import os
from typing import Any

from PyQt6.QtWidgets import QMainWindow, QSizePolicy, QWidget
from PyQt6.QtCore import Qt, QTimer, QEvent, QPoint, pyqtSignal

from neoarch.backend.services import network_latency
from neoarch.managers.plugin_manager import PluginsManager
from neoarch.frontend.icon_registry import icon_path
from neoarch.frontend.styles import Styles
from neoarch.frontend.themes import SYSTEM_THEME_ID, THEMES, ThemeManager
from neoarch.backend.services.settings import (
    DEFAULT_WINDOW_MODE,
    WINDOW_MODE_NEOARCH,
    WINDOW_MODE_SYSTEM,
)
from neoarch.frontend.components.title_bar import _get_brand_icon_path
from neoarch.frontend.mixins.icons import _IconsMixin, _build_window_icon
from neoarch.frontend.mixins.auth import _AuthMixin
from neoarch.frontend.mixins.plugins import _PluginsMixin
from neoarch.frontend.mixins.settings import _SettingsMixin
from neoarch.frontend.mixins.bundles import _BundlesMixin
from neoarch.frontend.mixins.search import _SearchMixin
from neoarch.frontend.mixins.filters import _FiltersMixin
from neoarch.frontend.mixins.views import _ViewsMixin
from neoarch.frontend.mixins.operations import _OperationsMixin

network_latency.install()
network_latency.start_probing()

class ArchPkgManagerUniGetUI(_ViewsMixin, _OperationsMixin, _BundlesMixin, _SearchMixin, _FiltersMixin, _PluginsMixin, _SettingsMixin, _AuthMixin, _IconsMixin, QMainWindow):
    packages_ready = pyqtSignal(list, object, bool)  # packages, load_id, is_final
    discover_results_ready = pyqtSignal(list)
    discover_suggestions_ready = pyqtSignal(str)
    show_message = pyqtSignal(str, str)
    log_signal = pyqtSignal(str)
    load_error = pyqtSignal()
    search_timer = QTimer()
    installation_progress = pyqtSignal(str, bool)  # status, can_cancel
    progress_update = pyqtSignal(str, int)  # message, percent (-1 = indeterminate)
    snapshot_progress = pyqtSignal(str, str)  # state ("busy"|"done"|"error"), detail
    ui_call = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        from neoarch.resources.paths import APP_EDITION
        self.setWindowTitle(f"NeoArch — {APP_EDITION} Edition")
        self.setGeometry(100, 100, 1600, 900)  # Increased width to accommodate sidebar
        self.setMinimumSize(1280, 850)  # Set minimum size (fits Discover dashboard without scroll)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._windowed_flags = (
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self._frameless_flags = (
            self._windowed_flags | Qt.WindowType.FramelessWindowHint
        )
        self.setStyleSheet(Styles.get_dark_stylesheet())
        self._ui_ready = False
        self._theme_manager = ThemeManager(self)
        self._theme_manager.theme_changed.connect(self._on_theme_changed)
        self._theme_manager.enable_system_tracking()
        self._theme_manager.load_saved()
        # Re-apply stylesheet after theme load
        self.setStyleSheet(Styles.get_dark_stylesheet())
        brand_path = _get_brand_icon_path()
        if os.path.exists(brand_path):
            self.setWindowIcon(_build_window_icon(brand_path))
        # self.set_minimal_icon()
        self._resize_margin = 6
        self._resize_edge = None
        self._edge_cursor = None
        self._resize_active = False
        self._resize_watchdog: Any = None
        self.setMouseTracking(True)
        try:
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().installEventFilter(self)
        except Exception:
            pass
        
        self.current_view = "updates"
        self._user_has_navigated = False
        self.updating = False
        self.all_packages = []
        self.search_results = []
        self.packages_per_page = 10
        self.current_page = 0
        self.loader_thread: Any = None
        self.git_manager: Any = None
        self.docker_manager: Any = None
        self.current_search_mode = 'both'
        self.filtered_results = []
        self.installed_index: Any = None
        self._installed_index_building = False
        self._installed_index_last_built = 0
        self._installed_index_sources = set()
        self._installed_filter_states = {"Updates available": False}
        # Working bundle state (list of {name,id,source,version?})
        self.bundle_items = []
        self._active_bundle_key = ""
        # Settings state
        self.settings = self.load_settings()
        if self._window_mode() == WINDOW_MODE_SYSTEM:
            if self._theme_manager.current_id != SYSTEM_THEME_ID:
                if (not self.settings.get('neoarch_theme')
                        and self._theme_manager.current_id in THEMES):
                    self.settings['neoarch_theme'] = self._theme_manager.current_id
                    self.save_settings()
                self._theme_manager.apply_theme(SYSTEM_THEME_ID)
        elif self._theme_manager.current_id == SYSTEM_THEME_ID:
            # A NeoArch frame always needs one of its own themes; System is
            # reserved for Native system mode.
            theme_id = self.settings.get('neoarch_theme') or 'dark'
            if theme_id == SYSTEM_THEME_ID or theme_id not in THEMES:
                theme_id = 'dark'
            self.settings['neoarch_theme'] = theme_id
            self.save_settings()
            self._theme_manager.apply_theme(theme_id)
        self.apply_logging_config()
        # Activate the saved UI/CLI language catalog
        try:
            from neoarch.backend.services.i18n import set_language, detect_system_language
            set_language(self.settings.get('culture') or detect_system_language() or 'en')
        except Exception:
            pass
        # Plugins runtime
        self.plugins = []
        self.plugin_timer = QTimer()
        self.plugin_timer.setInterval(60000)
        self.plugin_timer.timeout.connect(self.run_plugin_tick)
        self._icon_cache = {}
        self._source_icon_cache = {}
        self._discover_name_icon = self.get_svg_icon(icon_path("sources/packagename"), 20)
        self._discover_version_icon = self.get_svg_icon(icon_path("sources/version"), 18)
        self._flathub_checked = False
        self.plugins_manager = PluginsManager(self)
        self.packages_ready.connect(self.on_packages_loaded)
        self.discover_results_ready.connect(self.display_discover_results)
        self.discover_suggestions_ready.connect(self._on_discover_suggestions_ready)
        self.show_message.connect(self._show_message)
        self.log_signal.connect(self.log)
        self.load_error.connect(self.on_load_error)
        self.installation_progress.connect(self.on_installation_progress)
        self.progress_update.connect(self.on_progress_update)
        self.ui_call.connect(self._on_ui_call)
        # Background loading coordination
        self.loading_context: Any = None
        self.cancel_update_load = False
        self._updating_selection = False
        self._view_mode = "table"
        self._grid_view_btn = None
        self._news_btn = None
        self.cancel_discover_search = False
        # Nav badges (e.g., updates count)
        self.nav_badges = {}
        self.tray_icon: Any = None
        self._force_quit = False
        self._tray_notice_shown = False
        # Attributes initialized in other methods
        self.settings_widgets = {}
        self.settings_content_layout: Any = None
        self.settings_nav_buttons = {}
        self.source_card: Any = None
        self.filters_panel: Any = None

        # Cloud auth (Supabase sync)
        from neoarch.backend.cloud_auth import CloudAuthManager
        self._cloud_auth = CloudAuthManager()
        self._cloud_auth.login_changed.connect(self._on_cloud_user_changed)

        self._apply_window_mode_flags(self._window_mode(), initial=True)
        self.setup_ui()
        self.apply_window_effects()
        # Set initial nav button state
        for btn_id, btn in self.nav_buttons.items():
            btn.setChecked(btn_id == self.current_view)
        self.center_window()
        
        # Initialize the default view (UI only, no data loading — deferred to auth flow)
        self.switch_view(self.current_view, load=False)
        self._ui_ready = True

        self._setup_tray()

        # Show welcome animation in console on first launch
        QTimer.singleShot(500, self.show_welcome_animation)
        # Initialize plugins shortly after UI is ready
        QTimer.singleShot(1000, self.initialize_plugins)
        QTimer.singleShot(1200, self._prewarm_installed_index_async)
        
        # Debounce search input
        self.search_timer.setInterval(800)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        try:
            self.search_input.returnPressed.connect(self.perform_search)
        except Exception:
            pass
        QTimer.singleShot(1500, self.run_first_run_checks)
        # Restore cloud avatar UI state
        QTimer.singleShot(2000, lambda: self._on_cloud_user_changed(self._cloud_auth.user))
        # Release notes: What's New after an update, then silently detect newer releases
        QTimer.singleShot(3200, self._check_release_notes)
        # Clean up orphaned snapshot processes left over from a previously
        # interrupted session (they hold lock files and would freeze new runs)
        QTimer.singleShot(4000, self._cleanup_stale_snapshot_procs)

    def _setup_tray(self):
        """Create the system tray icon when the desktop supports one."""
        try:
            from neoarch.frontend.components.tray_icon import (
                TrayIcon, tray_available)
            if not tray_available():
                return
            self.tray_icon = TrayIcon(self, _get_brand_icon_path(), self)
            self.tray_icon.show()
            self.tray_icon.set_update_count(
                len(getattr(self, 'updates_all', []) or []))
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                app.setQuitOnLastWindowClosed(False)
        except Exception as e:
            try:
                self.log(f"Tray icon unavailable: {e}")
            except Exception:
                pass

    def _cleanup_stale_snapshot_procs(self):
        """Kill orphaned timeshift/snapper processes in the background."""
        try:
            from threading import Thread
            from neoarch.backend.services.snapshot import kill_stale_snapshot_procs
            Thread(target=kill_stale_snapshot_procs, daemon=True).start()
        except Exception:
            pass

    def _on_cloud_user_changed(self, user):
        if hasattr(self, 'update_user_avatar'):
            self.update_user_avatar(user)
        if hasattr(self, '_update_nav_greeting'):
            self._update_nav_greeting(user)
        if hasattr(self, '_update_bundle_buttons'):
            self._update_bundle_buttons()

    def _window_mode(self):
        """Return the saved window mode, falling back to the system default."""
        mode = str(self.settings.get('window_mode', DEFAULT_WINDOW_MODE))
        if mode in (WINDOW_MODE_SYSTEM, WINDOW_MODE_NEOARCH):
            return mode
        return DEFAULT_WINDOW_MODE

    def _apply_window_mode_flags(self, mode, initial=False):
        """Switch between native OS decorations and the NeoArch frame."""
        native = mode == WINDOW_MODE_SYSTEM
        flags = self._windowed_flags if native else self._frameless_flags
        was_visible = self.isVisible()
        was_maximized = self.isMaximized()
        geometry = self.geometry()
        if flags != self.windowFlags():
            self.setWindowFlags(flags)
        transparent = (
            not native
            or bool(self.settings.get('window_system_transparency', False))
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, transparent)
        title_bar = getattr(self, '_title_bar', None)
        if title_bar is not None:
            title_bar.setVisible(not native)
        if not initial and was_visible:
            self.show()
            if was_maximized:
                self.showMaximized()
            else:
                self.setGeometry(geometry)

    def refresh_window_mode(self):
        """Reapply window flags and effects after appearance changes."""
        self._apply_window_mode_flags(self._window_mode())
        self.apply_window_effects()

    def set_window_mode(self, mode):
        """Apply Native system or NeoArch window styling and persist it."""
        if mode not in (WINDOW_MODE_SYSTEM, WINDOW_MODE_NEOARCH):
            return
        if mode == self._window_mode():
            return
        manager = getattr(self, '_theme_manager', None)
        if mode == WINDOW_MODE_SYSTEM:
            if manager is not None and manager.current_id in THEMES:
                self.settings['neoarch_theme'] = manager.current_id
            self.settings['window_mode'] = WINDOW_MODE_SYSTEM
            self.save_settings()
            self.refresh_window_mode()
            applied = manager.apply_theme(SYSTEM_THEME_ID) if manager else False
            if not applied:
                QTimer.singleShot(0, self.rebuild_ui)
        else:
            theme_id = self.settings.get('neoarch_theme') or 'dark'
            if theme_id == SYSTEM_THEME_ID or theme_id not in THEMES:
                theme_id = 'dark'
            self.settings['neoarch_theme'] = theme_id
            self.settings['window_mode'] = WINDOW_MODE_NEOARCH
            self.save_settings()
            self.refresh_window_mode()
            applied = manager.apply_theme(theme_id) if manager else False
            if not applied:
                QTimer.singleShot(0, self.rebuild_ui)

    def _on_theme_changed(self, theme_id):
        """Reapply the stylesheet and rebuild widgets that cache colors."""
        from neoarch.frontend import tokens
        self.setStyleSheet(tokens.DARK_STYLESHEET)
        try:
            from neoarch.frontend.components.dark_dialogs import refresh_open_dialogs
            refresh_open_dialogs()
        except Exception:
            pass
        if getattr(self, '_ui_ready', False):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self.rebuild_ui)

    def _check_release_notes(self):
        """Show 'What's New' once after the app updates.

        Dev preview toggles (skip the once-per-version logic):
          NEOARCH_PREVIEW_WHATS_NEW=1        force the What's New dialog
          NEOARCH_PREVIEW_UPDATE=3.2.0       force the update-available dialog
        """
        import os as _os
        try:
            from neoarch.resources.paths import APP_VERSION
            from neoarch.backend.services.release_notes import (
                parse_changelog, whats_new)
            from neoarch.frontend.components.whats_new_dialog import (
                WhatIsNewDialog)
        except Exception as e:
            self.log(f"Release notes init failed: {e}")
            return

        blocks = parse_changelog()
        last_seen = str(self.settings.get('last_seen_version', '') or '')

        preview_wn = _os.environ.get('NEOARCH_PREVIEW_WHATS_NEW')
        preview_up = _os.environ.get('NEOARCH_PREVIEW_UPDATE')
        if preview_wn:
            WhatIsNewDialog(
                whats_new(blocks, '', limit=4), mode='whats_new',
                current_version=APP_VERSION, parent=self).exec()
            return
        if preview_up:
            info = {
                'version': preview_up.strip(),
                'name': preview_up.strip(),
                'body': '',
                'html_url': 'https://github.com/sanjayadanushka712/Neoarch/releases/latest',
            }
            WhatIsNewDialog([], mode='update', latest=info,
                            parent=self).exec()
            return

        if APP_VERSION != last_seen:
            seen = whats_new(blocks, last_seen)
            if seen:
                self.settings['last_seen_version'] = APP_VERSION
                try:
                    WhatIsNewDialog(
                        seen, mode='whats_new',
                        current_version=APP_VERSION, parent=self).exec()
                finally:
                    self.save_settings()

    def close_to_tray_active(self):
        """True when closing the window should keep NeoArch in the tray."""
        if not self.settings.get('close_to_tray', False):
            return False
        tray = getattr(self, 'tray_icon', None)
        try:
            return tray is not None and tray.isVisible()
        except Exception:
            return False

    def show_tray_notice(self):
        """Tell the user the app is still running in the tray (once)."""
        if getattr(self, '_tray_notice_shown', False):
            return
        self._tray_notice_shown = True
        try:
            from neoarch.backend.services.i18n import _
            from PyQt6.QtWidgets import QSystemTrayIcon
            self.tray_icon.showMessage(
                _("NeoArch is running"),
                _("Open NeoArch from the system tray icon."),
                QSystemTrayIcon.MessageIcon.Information, 4000)
        except Exception:
            pass

    def request_quit(self):
        """Quit explicitly, bypassing close-to-tray behavior."""
        self._force_quit = True
        tray = getattr(self, 'tray_icon', None)
        if tray is not None:
            try:
                tray.hide()
            except Exception:
                pass
        self.close()

    def closeEvent(self, event):
        if not getattr(self, '_force_quit', False) and self.close_to_tray_active():
            event.ignore()
            self.hide()
            self.show_tray_notice()
            return
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
                app.setQuitOnLastWindowClosed(True)
            # Force one full synchronous repaint before accepting the close so
            # the compositor's close fade composites the complete frame
            # (content + rounded border) instead of the border lagging a few
            # frames behind the disappearing body.
            self.repaint()
            if app is not None:
                app.processEvents()
        except Exception:
            pass
        super().closeEvent(event)

    # ── Frameless window edge resizing ──────────────────────────────

    def _edge_at(self, pos: QPoint):
        if self.isMaximized() or self.isFullScreen():
            return None
        w, h = self.width(), self.height()
        m = self._resize_margin
        x, y = pos.x(), pos.y()
        left = x <= m
        right = x >= w - m
        top = y <= m
        bottom = y >= h - m
        if left and top:
            return Qt.Edge.TopEdge | Qt.Edge.LeftEdge
        if right and top:
            return Qt.Edge.TopEdge | Qt.Edge.RightEdge
        if left and bottom:
            return Qt.Edge.LeftEdge | Qt.Edge.BottomEdge
        if right and bottom:
            return Qt.Edge.RightEdge | Qt.Edge.BottomEdge
        if left:
            return Qt.Edge.LeftEdge
        if right:
            return Qt.Edge.RightEdge
        if top:
            return Qt.Edge.TopEdge
        if bottom:
            return Qt.Edge.BottomEdge
        return None

    @staticmethod
    def _cursor_for_edge(edge):
        corners = {
            Qt.Edge.TopEdge | Qt.Edge.LeftEdge: Qt.CursorShape.SizeFDiagCursor,
            Qt.Edge.BottomEdge | Qt.Edge.RightEdge: Qt.CursorShape.SizeFDiagCursor,
            Qt.Edge.TopEdge | Qt.Edge.RightEdge: Qt.CursorShape.SizeBDiagCursor,
            Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeBDiagCursor,
        }
        if edge in corners:
            return corners[edge]
        shapes = {
            Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor,
            Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor,
            Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor,
            Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
        }
        return shapes.get(edge)

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype in (QEvent.Type.MouseButtonRelease, QEvent.Type.Resize):
            if self._resize_active:
                self._resize_active = False
                self._stop_resize_watchdog()
                self.unsetCursor()
                self._edge_cursor = None
            if etype == QEvent.Type.Resize:
                return super().eventFilter(obj, event)
        elif etype in (QEvent.Type.WindowDeactivate, QEvent.Type.ApplicationStateChange):
            # Alt-tabbing away mid-resize can leave the hand-off dangling with
            # no release/resize event to unset the gate — clear defensively.
            if self._resize_active:
                self._resize_active = False
                self._stop_resize_watchdog()
                self.unsetCursor()
                self._edge_cursor = None
                self.log("Resize hand-off cancelled (window deactivated)")
        if etype == QEvent.Type.MouseMove or etype == QEvent.Type.MouseButtonPress:
            if self.isMaximized() or self.isFullScreen():
                return super().eventFilter(obj, event)
            if not (isinstance(obj, QWidget) and obj.window() is self):
                return super().eventFilter(obj, event)
            if self._resize_active:
                return True
            local = obj.mapTo(self, event.position().toPoint())
            edge = self._edge_at(local)
            if etype == QEvent.Type.MouseMove:
                if edge is not None:
                    self._edge_cursor = self._cursor_for_edge(edge)
                    self.setCursor(self._edge_cursor)
                elif self._edge_cursor is not None:
                    self._edge_cursor = None
                    self.unsetCursor()
            elif etype == QEvent.Type.MouseButtonPress:
                if edge is not None and event.button() == Qt.MouseButton.LeftButton:
                    handle = self.windowHandle()
                    if handle is not None:
                        self._resize_active = True
                        self._start_resize_watchdog()
                        handle.startSystemResize(edge)
                        return True
        return super().eventFilter(obj, event)

    def _start_resize_watchdog(self):
        """Arm a single-shot guard that releases the resize gate if the
        window-manager hand-off never sends a confirming release/resize."""
        try:
            self._resize_watchdog = QTimer(self)
            self._resize_watchdog.setSingleShot(True)
            self._resize_watchdog.setInterval(1500)
            self._resize_watchdog.timeout.connect(self._resize_watchdog_fired)
            self._resize_watchdog.start()
        except Exception:
            pass

    def _stop_resize_watchdog(self):
        if self._resize_watchdog is not None:
            try:
                self._resize_watchdog.stop()
            except Exception:
                pass
            self._resize_watchdog = None

    def _resize_watchdog_fired(self):
        if not self._resize_active:
            return
        self._resize_active = False
        self._resize_watchdog = None
        self.unsetCursor()
        self._edge_cursor = None
        self.log("Resize hand-off timed out; released the resize gate")


