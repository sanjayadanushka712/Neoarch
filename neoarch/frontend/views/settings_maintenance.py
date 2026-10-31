"""Maintenance settings page — descriptive, education-first.

Explains what each tidy-up task does and *why* you would run it, built
with the same card language as the Security, Logging and Proxy pages.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget)

from neoarch.backend.services.hygiene import news_unseen_count
from neoarch.frontend.tokens import Colors, Fonts, QSS
from neoarch.backend.services.i18n import _
from neoarch.frontend.views._settings_kit import make_card, row, sep, Stepper

# ── Inline stroke icons (24x24 viewBox, lucide-style) ──────────────
_ICON_TRASH = (
    '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>'
    '<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>'
    '<line x1="10" x2="10" y1="11" y2="17"/>'
    '<line x1="14" x2="14" y1="11" y2="17"/>'
)
_ICON_GEAR = (
    '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82'
    'l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33'
    'a1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9'
    '19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06'
    'a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09'
    'A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83'
    'a2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3'
    'a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33'
    'l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9'
    'a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51'
    '1z"/>'
)
_ICON_DATABASE = (
    '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
    '<path d="M3 5V19A9 3 0 0 0 21 19V5"/>'
    '<path d="M3 12A9 3 0 0 0 21 12"/>'
)
_ICON_NEWS = (
    '<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16'
    'a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>'
    '<path d="M18 14h-8"/><path d="M15 18h-5"/>'
    '<path d="M10 6h8v4h-8V6Z"/>'
)
_ICON_GLOBE = (
    '<circle cx="12" cy="12" r="10"/>'
    '<path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>'
    '<path d="M2 12h20"/>'
)


def _action(text, on_click):
    btn = QPushButton(text)
    btn.setStyleSheet(QSS.BTN_OUTLINE)
    btn.setFixedHeight(36)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.clicked.connect(on_click)
    return btn


class MaintenanceSettingsWidget(QWidget):
    # Emitted from the news-count worker thread; updates the button label.
    _news_count_ready = pyqtSignal(int)
    # Emitted from the mirror-refresh worker thread: (ok, detail).
    _mirror_done = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = parent
        self._news_count_ready.connect(self._set_news_badge)
        self._mirror_done.connect(self._on_mirror_done)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self.setup_ui()

    def scan_corrupted(self):
        from neoarch.backend.services.hygiene import list_corrupted_packages
        from threading import Thread

        def task():
            try:
                corrupted = list_corrupted_packages()
            except Exception as e:
                corrupted = None
                err = str(e)
            if corrupted is None:
                self.app.show_message.emit(
                    "Cache Scan", _("Scan failed: {err}").format(err=err))
                return
            if not corrupted:
                self.app.show_message.emit(
                    "Cache Scan", _("No corrupted package archives found."))
            else:
                self.app.show_message.emit(
                    "Cache Scan",
                    _("Found {n} corrupted archive(s):\n{list}").format(
                        n=len(corrupted), list=", ".join(corrupted[:10]))
                    + ("\n..." if len(corrupted) > 10 else ""))

        Thread(target=task, daemon=True).start()

    def purge_cache(self):
        from neoarch.backend.services.hygiene import purge_cache
        from threading import Thread

        def task():
            ok = purge_cache(retain=self.cache_keep.value())
            if ok:
                self.app.show_message.emit(
                    "Cache Purge", _("Old cached versions removed."))
            else:
                self.app.show_message.emit(
                    "Cache Purge", _("Nothing to purge (or failed)."))

        Thread(target=task, daemon=True).start()

    def refresh_mirrors(self):
        from neoarch.backend.services.mirrors import (
            refresh_mirrors, reflector_path)
        from threading import Thread

        if not reflector_path():
            self.app.show_message.emit(
                "Mirrors",
                _("reflector isn't installed. Install the 'reflector' "
                  "package first."))
            return
        latest = self.mirror_count.value()
        self.mirror_btn.setEnabled(False)
        self.mirror_btn.setText(_("Refreshing…"))

        def task():
            ok, detail = refresh_mirrors(latest=latest)
            try:
                self._mirror_done.emit(ok, detail)
            except RuntimeError:
                pass  # widget destroyed during the refresh

        Thread(target=task, daemon=True).start()

    def _on_mirror_done(self, ok: bool, detail: str):
        try:
            self.mirror_btn.setEnabled(True)
            self.mirror_btn.setText(_("Refresh Mirrors"))
        except RuntimeError:
            pass
        if ok:
            self.app.show_message.emit(
                "Mirrors",
                _("Mirror list updated with {n} servers.").format(n=detail))
        else:
            self.app.show_message.emit(
                "Mirrors",
                _("Mirror refresh failed: {err}").format(err=detail))

    def setup_ui(self):
        title = QLabel(_("Maintenance"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(
            _("Keep your system tidy: orphans, leftover configs, the "
              "download cache, and Arch news"))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent; margin-top: 0;")
        self.layout.addWidget(subtitle)

        # ── Orphans ──
        orphans_card, orphans = make_card(_("Orphaned Packages"), _ICON_TRASH)
        orphans.addWidget(row(
            _("Remove orphaned packages"),
            _("Packages installed as dependencies that nothing needs any "
              "more. Deleting them is safe, frees disk space and makes "
              "updates faster."),
            control=_action(_("Remove Orphans"), self.app.cleanup_orphans)))
        self.layout.addWidget(orphans_card)

        # ── .pacnew ──
        pacnew_card, pacnew = make_card(_("Config Files (.pacnew)"), _ICON_GEAR)
        pacnew.addWidget(row(
            _("Manage .pacnew files"),
            _("When a package ships a new config, the old one is kept as a "
              ".pacnew. Review and merge them so your tweaks are never "
              "silently lost."),
            control=_action(_("Manage .pacnew"), self.app.manage_pacnew)))
        self.layout.addWidget(pacnew_card)

        # ── Download Cache ──
        cache_card, cache = make_card(_("Download Cache"), _ICON_DATABASE)
        cache.addWidget(row(
            _("Scan for corrupted archives"),
            _("Check cached package archives for corruption before they "
              "cause an install to fail."),
            control=_action(
                _("Scan for Corrupted Archives"), self.scan_corrupted)))
        cache.addWidget(sep())
        self.cache_keep = Stepper(1, 10)
        self.cache_keep.setValue(3)

        keep_control = QWidget()
        keep_control.setStyleSheet("background: transparent;")
        keep_lay = QHBoxLayout(keep_control)
        keep_lay.setContentsMargins(0, 0, 0, 0)
        keep_lay.setSpacing(8)
        keep_lay.addWidget(self.cache_keep)
        keep_lay.addWidget(_action(_("Purge Old Cache"), self.purge_cache))
        cache.addWidget(row(
            _("Keep versions per package"),
            _("How many old versions to keep before purging. Keep it "
              "small \u2014 older archives are already installed."),
            control=keep_control))
        self.layout.addWidget(cache_card)

        # ── Arch News ──
        news_card, news = make_card(_("Arch Linux News"), _ICON_NEWS)
        self._news_btn = _action(_("Show News"), self.app.show_arch_news)
        self._load_news_count_async()
        news.addWidget(row(
            _("Read the news before updating"),
            _("Important announcements such as manual interventions are "
              "posted before big changes land. Worth a glance before "
              "major upgrades."),
            control=self._news_btn))
        self.layout.addWidget(news_card)

        # ── Package Mirrors ──
        mirrors_card, mirrors = make_card(
            _("Package Mirrors"), _ICON_GLOBE)
        self.mirror_count = Stepper(3, 20)
        self.mirror_count.setValue(10)
        mirrors.addWidget(row(
            _("Latest mirrors"),
            _("How many mirrors to keep. Fewer means faster syncs; more "
              "means more fallbacks when one goes down."),
            control=self.mirror_count))
        mirrors.addWidget(sep())
        self.mirror_btn = _action(
            _("Refresh Mirrors"), self.refresh_mirrors)
        mirrors.addWidget(row(
            _("Refresh mirror list"),
            _("Download the fastest HTTPS mirrors with reflector and write "
              "them to /etc/pacman.d/mirrorlist. Reflector must be "
              "installed."),
            control=self.mirror_btn))
        self.layout.addWidget(mirrors_card)

    def _load_news_count_async(self):
        """Resolve the unread-news badge off the UI thread.

        news_unseen_count() performs a synchronous RSS fetch; running it
        inline used to freeze the first Settings open for seconds.
        """
        from threading import Thread

        def task():
            try:
                n = news_unseen_count()
            except Exception:
                return
            if n:
                try:
                    self._news_count_ready.emit(int(n))
                except RuntimeError:
                    pass  # widget destroyed during a rebuild

        Thread(target=task, daemon=True).start()

    def _set_news_badge(self, n: int):
        try:
            self._news_btn.setText(
                _("Show News ({n} new)").format(n=n))
        except RuntimeError:
            pass  # widget already destroyed
