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

# ── Card icons (assets/icons/ui) ───────────────────────────────────
_ICON_TRASH = "ui/trash"
_ICON_GEAR = "ui/gear"
_ICON_DATABASE = "ui/database"
_ICON_NEWS = "ui/news-line"
_ICON_GLOBE = "ui/globe"


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
            available_mirror_tool, refresh_mirrors)
        from threading import Thread

        if not available_mirror_tool():
            self.app.show_message.emit(
                "Mirrors",
                _("No supported mirror tool is installed. Install reflector, "
                  "pacman-mirrors, or cachyos-rate-mirrors for your "
                  "distribution."))
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
            _("Download the fastest mirrors with your distribution's "
              "supported tool and write them to the system mirror list. "
              "NeoArch uses reflector, pacman-mirrors, or "
              "cachyos-rate-mirrors automatically."),
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
