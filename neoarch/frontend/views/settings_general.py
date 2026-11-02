import os
import time
import json
import functools
from typing import Any
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox,
                             QFrame)

from neoarch.backend import sys_utils
from neoarch.backend.services.i18n import _, language_label, available_languages, set_language, detect_system_language
from neoarch.frontend.icon_registry import render_pixmap
from neoarch.frontend.tokens import QSS, Colors, Fonts, Radii
from neoarch.frontend.components.toggle_switch import ToggleSwitch

# ── Card icons (assets/icons/ui) ───────────────────────────────────
_ICON_SLIDERS = "ui/sliders"
_ICON_PACKAGE = "ui/package"
_ICON_SAVE = "ui/save"
_ICON_SIGNAL = "ui/signal"
_ICON_DATABASE = "ui/database"
_ICON_TRAY = "ui/monitor"


class _AurApiTestThread(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        t0 = time.time()
        try:
            from neoarch.backend.services.network import urlopen as _urlopen
            with _urlopen(
                "https://aur.archlinux.org/rpc/?v=5&type=info&arg[]=bash",
                timeout=15,
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            ms = (time.time() - t0) * 1000
            self.finished.emit({"ok": True, "ms": ms, "data": data, "err": ""})
        except Exception as err:
            ms = (time.time() - t0) * 1000
            self.finished.emit({"ok": False, "ms": ms, "data": None, "err": str(err)})


class GeneralSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app: Any = parent
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(24)
        self._aur_thread = None
        self._source_rows = []

        self.setup_ui()

    # ── building blocks (About-page pattern) ────────────────────────

    @staticmethod
    def _icon_pixmap(icon_name, size=14, color=None):
        return render_pixmap(icon_name, size, color or Colors.TEXT)

    @staticmethod
    def _make_card(title_text, svg_body=None):
        """A flat settings card, exactly like the About page."""
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setStyleSheet(QSS.CARD)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 12)
        card_layout.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(10)
        if svg_body is not None:
            badge = QLabel()
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background: {Colors.SURFACE_2}; border: none;"
                f" border-radius: {Radii.SM}px;")
            badge.setPixmap(GeneralSettingsWidget._icon_pixmap(svg_body, 15))
            header.addWidget(badge)
        title = QLabel(title_text)
        title.setStyleSheet(
            f"font-size: {Fonts.CARD_TITLE}; font-weight: {Fonts.SEMI};"
            f" color: {Colors.TEXT}; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        card_layout.addLayout(header)

        pad = QWidget()
        pad.setStyleSheet("background: transparent;")
        pad.setFixedHeight(2)
        card_layout.addWidget(pad)
        return card, card_layout

    @staticmethod
    def _row(title_text, subtitle_text=None, subtitle_color=None, control=None,
             capture=None):
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        row = QHBoxLayout(row_widget)
        row.setSpacing(16)
        row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        texts = QVBoxLayout()
        texts.setSpacing(2)

        title = QLabel(title_text)
        title.setStyleSheet(
            f"font-size: {Fonts.BASE}; font-weight: {Fonts.MEDIUM};"
            f" color: {Colors.TEXT}; border: none; background: transparent;")
        texts.addWidget(title)

        if subtitle_text:
            color = subtitle_color or Colors.TEXT_2
            subtitle = QLabel(subtitle_text)
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet(
                f"font-size: {Fonts.SM}; color: {color};"
                " border: none; background: transparent;")
            texts.addWidget(subtitle)
            if isinstance(capture, dict):
                capture["subtitle"] = subtitle

        row.addLayout(texts, 1)
        if control is not None:
            row.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        return row_widget

    def _add_source_toggle(self, layout, key, title, desc_ok, desc_missing,
                           binary, pkg, tool):
        """Build one optional-integration toggle whose disabled state tracks
        whether ``binary`` is present on the system.  ``refresh_source_states``
        re-evaluates them all (e.g. when Settings is re-opened)."""
        toggle = ToggleSwitch(self, title)
        toggle.setChecked(bool(self.app.settings.get(key, True)), animate=False)
        toggle.toggled.connect(lambda v, k=key: self.app.update_setting(k, v))
        capture = {}
        layout.addWidget(self._row(title, desc_ok, control=toggle,
                                   capture=capture))
        self._source_rows.append({
            "toggle": toggle,
            "subtitle": capture.get("subtitle"),
            "desc_ok": desc_ok,
            "desc_missing": desc_missing,
            "binary": binary, "pkg": pkg, "tool": tool,
        })
        return toggle

    def refresh_source_states(self):
        """Re-check tool availability and update the toggles/subtitles.

        Idempotent and cheap: only re-runs ``cmd_exists`` on three binaries.
        Keeps a package-installed-mid-session toggle from staying greyed out.
        """
        for entry in self._source_rows:
            missing = not sys_utils.cmd_exists(entry["binary"])
            toggle = entry["toggle"]
            toggle.setEnabled(not missing)
            toggle.setToolTip(
                "" if not missing else entry["desc_missing"])
            subtitle = entry["subtitle"]
            if subtitle is not None:
                subtitle.setText(entry["desc_missing"] if missing
                                 else entry["desc_ok"])
                subtitle.setStyleSheet(
                    f"font-size: {Fonts.SM};"
                    f" color: {Colors.RED if missing else Colors.TEXT_2};"
                    " border: none; background: transparent;")

    @staticmethod
    def _sep():
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(
            f"background: {Colors.BORDER}; border: none; margin: 4px 0;")
        return line

    @staticmethod
    def _btn(text, on_click=None):
        """Quiet light button — same look as the About page links."""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER_HOVER};
                border-radius: 10px;
                padding: 8px 18px;
                font-size: {Fonts.BASE};
                font-weight: {Fonts.MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER_HOVER};
                border-color: {Colors.ACCENT_40};
            }}
            QPushButton:pressed {{
                background-color: {Colors.OVERLAY_14};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_3};
                border-color: {Colors.BORDER};
                background-color: transparent;
            }}
        """)
        btn.setFixedHeight(36)
        if on_click is not None:
            btn.clicked.connect(lambda checked=False: on_click())
        return btn

    # ── UI ─────────────────────────────────────────────────────────

    def setup_ui(self):
        title = QLabel(_("General"))
        title.setStyleSheet(
            f"font-size: {Fonts.PAGE_TITLE}; font-weight: {Fonts.BOLD};"
            f" color: {Colors.TEXT}; letter-spacing: -0.5px;")
        self.layout.addWidget(title)

        subtitle = QLabel(_("Configure basic application settings and preferences"))
        subtitle.setStyleSheet(
            f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
            " border: none; background: transparent;")
        self.layout.addWidget(subtitle)

        # ── Basic Settings ──
        basic_card, basic_layout = self._make_card(_("Basic Settings"), _ICON_SLIDERS)

        self.sw_auto_check = ToggleSwitch(self, _("Auto check updates on launch"))
        self.sw_auto_check.setChecked(bool(self.app.settings.get('auto_check_updates', True)), animate=False)
        self.sw_auto_check.toggled.connect(lambda v: self.app.update_setting('auto_check_updates', v))
        basic_layout.addWidget(self._row(
            _("Auto check updates on launch"),
            _("Checks for available updates each time the app starts."),
            control=self.sw_auto_check))
        basic_layout.addWidget(self._sep())

        self.sw_firmware = self._add_source_toggle(
            basic_layout,
            key='include_firmware_updates',
            title=_("Check for firmware updates"),
            desc_ok=_("Detects firmware updates via fwupd on the Updates page. "
                      "Applying always requires your explicit confirmation."),
            desc_missing=_("fwupd is not installed — install with: sudo pacman -S fwupd"),
            binary="fwupdmgr", pkg="fwupd", tool="fwupd")
        basic_layout.addWidget(self._sep())

        self.sw_pipx = self._add_source_toggle(
            basic_layout,
            key='check_pipx_updates',
            title=_("Check for pipx updates"),
            desc_ok=_("Detects apps installed with pipx (Python scripts) and lists "
                      "their updates on the Updates page."),
            desc_missing=_("pipx is not installed — install with: sudo pacman -S python-pipx"),
            binary="pipx", pkg="pipx", tool="pipx")
        basic_layout.addWidget(self._sep())

        self.sw_npm = self._add_source_toggle(
            basic_layout,
            key='npm_user_mode',
            title=_("Use npm user mode"),
            desc_ok=_("Installs global npm packages to ~/.npm-global without sudo."),
            desc_missing=_("npm is not installed — install with: sudo pacman -S npm"),
            binary="npm", pkg="npm", tool="npm")

        self.layout.addWidget(basic_card)

        # ── Startup & Tray ──
        tray_card, tray_layout = self._make_card(_("Startup & Tray"), _ICON_TRAY)
        try:
            from neoarch.frontend.components.tray_icon import tray_available
            tray_ok = tray_available()
        except Exception:
            tray_ok = False

        self.sw_start_minimized = ToggleSwitch(self, _("Start minimized"))
        self.sw_start_minimized.setChecked(bool(
            self.app.settings.get('start_minimized', False)), animate=False)
        self.sw_start_minimized.setEnabled(tray_ok)
        self.sw_start_minimized.toggled.connect(
            lambda v: self.app.update_setting('start_minimized', v))
        tray_layout.addWidget(self._row(
            _("Start minimized"),
            _("Start hidden in the system tray. Useful when NeoArch is "
              "launched from your desktop's autostart entry."),
            control=self.sw_start_minimized))
        tray_layout.addWidget(self._sep())

        self.sw_close_to_tray = ToggleSwitch(self, _("Close to tray"))
        self.sw_close_to_tray.setChecked(bool(
            self.app.settings.get('close_to_tray', False)), animate=False)
        self.sw_close_to_tray.setEnabled(tray_ok)
        self.sw_close_to_tray.toggled.connect(
            lambda v: self.app.update_setting('close_to_tray', v))
        tray_layout.addWidget(self._row(
            _("Close to tray"),
            _("Keep NeoArch running in the system tray when the window is "
              "closed. Quit from the tray menu."),
            control=self.sw_close_to_tray))

        if not tray_ok:
            message = _("System tray is not available on this desktop.")
            self.sw_start_minimized.setToolTip(message)
            self.sw_close_to_tray.setToolTip(message)

        self.layout.addWidget(tray_card)

        # ── Package Sources ──
        sources_card, sources_layout = self._make_card(_("Package Sources"), _ICON_PACKAGE)

        aur_status = sys_utils.get_aur_helper()
        if aur_status:
            aur_note = f"{_('Currently using')}: {aur_status}"
            aur_color = Colors.TEXT_2
        else:
            aur_note = _("No AUR helper detected")
            aur_color = Colors.RED

        self.aur_helper_combo = QComboBox()
        self.aur_helper_combo.setStyleSheet(QSS.COMBO)
        self.aur_helper_combo.setMinimumWidth(210)

        available_helpers = sys_utils.get_available_aur_helpers()
        self.aur_helper_combo.addItem(_("Auto (detect available)"), "auto")
        for helper in ['yay', 'paru', 'trizen', 'pikaur']:
            label = helper if helper in available_helpers else f"{helper} ({_('not installed')})"
            self.aur_helper_combo.addItem(label, helper)

        current_helper = self.app.settings.get('aur_helper', 'auto')
        index = self.aur_helper_combo.findData(current_helper)
        if index >= 0:
            self.aur_helper_combo.setCurrentIndex(index)

        self.aur_helper_combo.currentIndexChanged.connect(self.on_aur_helper_changed)
        sources_layout.addWidget(self._row(
            _("AUR Helper"),
            aur_note,
            subtitle_color=aur_color,
            control=self.aur_helper_combo))
        sources_layout.addWidget(self._sep())

        self.culture_combo = QComboBox()
        self.culture_combo.setStyleSheet(QSS.COMBO)
        self.culture_combo.setMinimumWidth(210)
        try:
            langs = available_languages()
        except Exception:
            langs = []
        for lang in ["en"] + langs:
            self.culture_combo.addItem(language_label(lang), lang)

        current_culture = self.app.settings.get('culture') or detect_system_language() or 'en'
        self.culture_combo.blockSignals(True)
        index = self.culture_combo.findData(current_culture)
        if index >= 0:
            self.culture_combo.setCurrentIndex(index)
        self.culture_combo.blockSignals(False)
        self.culture_combo.currentIndexChanged.connect(self.on_culture_changed)
        sources_layout.addWidget(self._row(
            _("Language"),
            _("Applies to all pages immediately."),
            control=self.culture_combo))

        self.layout.addWidget(sources_card)

        # ── Bundle Autosave ──
        bundle_card, bundle_layout = self._make_card(_("Bundle Autosave"), _ICON_SAVE)

        self.sw_bsave = ToggleSwitch(self, _("Autosave bundle to file"))
        self.sw_bsave.setChecked(bool(self.app.settings.get('bundle_autosave', True)), animate=False)
        self.sw_bsave.toggled.connect(lambda v: self.app.update_setting('bundle_autosave', v))
        bundle_layout.addWidget(self._row(
            _("Autosave bundle to file"),
            _("Save the selected bundle automatically."),
            control=self.sw_bsave))
        bundle_layout.addWidget(self._sep())

        from_path = self.app.settings.get('bundle_autosave_path') or os.path.join(
            os.path.expanduser('~'), '.config', 'neoarch', 'bundles', 'default.json')
        try:
            os.makedirs(os.path.dirname(from_path), exist_ok=True)
        except Exception:
            pass

        self.path_edit = QLineEdit(from_path)
        self.path_edit.setStyleSheet(QSS.LINEEDIT)
        self.path_edit.setMinimumWidth(260)

        browse_btn = QPushButton(_("Browse…"))
        browse_btn.setStyleSheet(QSS.BTN_OUTLINE)
        browse_btn.setFixedHeight(36)

        def on_browse():
            path, _filter = QFileDialog.getSaveFileName(self, _("Select Bundle Autosave Path"),
                                                   from_path, "Bundle JSON (*.json)")
            if path:
                self.path_edit.setText(path)
                self.app.update_setting('bundle_autosave_path', path)

        browse_btn.clicked.connect(on_browse)

        path_control = QWidget()
        path_control.setStyleSheet("background: transparent;")
        path_control_layout = QHBoxLayout(path_control)
        path_control_layout.setContentsMargins(0, 0, 0, 0)
        path_control_layout.setSpacing(8)
        path_control_layout.addWidget(self.path_edit)
        path_control_layout.addWidget(browse_btn)

        bundle_layout.addWidget(self._row(
            _("Autosave path"),
            control=path_control))

        self.layout.addWidget(bundle_card)

        # ── Diagnostics ──
        diag_card, diag_layout = self._make_card(_("Diagnostics"), _ICON_SIGNAL)

        self.aur_test_btn = self._btn(_("Test AUR API"), self.test_aur_api)
        self.aur_test_btn.setMinimumWidth(132)
        diag_layout.addWidget(self._row(
            _("AUR RPC endpoint"),
            _("Verifies reachability of the AUR RPC endpoint used to resolve"
              " packages from the AUR source."),
            control=self.aur_test_btn))

        self.aur_result = QLabel(_("Idle"))
        self.aur_result.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM};"
            " border: none; background: transparent; padding: 8px 4px 4px 4px;")
        diag_layout.addWidget(self.aur_result)

        self.layout.addWidget(diag_card)

        # ── Data ──
        data_card, data_layout = self._make_card(_("Data"), _ICON_DATABASE)

        export_btn = self._btn(_("Export Settings"), functools.partial(self.app.export_settings))
        export_btn.setMinimumWidth(132)
        data_layout.addWidget(self._row(
            _("Export settings to file"),
            control=export_btn))
        data_layout.addWidget(self._sep())

        import_btn = self._btn(_("Import Settings"), functools.partial(self.app.import_settings))
        import_btn.setMinimumWidth(132)
        data_layout.addWidget(self._row(
            _("Import settings from file"),
            control=import_btn))

        self.layout.addWidget(data_card)

        self.layout.addStretch()

        self.refresh_source_states()

    def on_aur_helper_changed(self, index):
        helper = self.aur_helper_combo.currentData()
        self.app.update_setting('aur_helper', helper)

    def on_culture_changed(self, index):
        culture = self.culture_combo.currentData()
        self.app.update_setting('culture', culture)
        try:
            set_language(culture or 'en')
        except Exception:
            pass
        QTimer.singleShot(0, functools.partial(self.app.rebuild_ui))

    def test_aur_api(self):
        if self._aur_thread is not None and self._aur_thread.isRunning():
            return
        self.aur_test_btn.setEnabled(False)
        self.aur_result.setText(_("Testing…"))
        self.aur_result.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM};"
            " border: none; background: transparent; padding: 8px 4px 4px 4px;")
        self._aur_thread = _AurApiTestThread(self)
        self._aur_thread.finished.connect(self._on_aur_test_done)
        self._aur_thread.start()

    def _on_aur_test_done(self, result):
        self.aur_test_btn.setEnabled(True)
        self.aur_result.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM};"
            " border: none; background: transparent; padding: 8px 4px 4px 4px;")
        if result.get("ok"):
            text = _("OK")
            data = result.get("data") or {}
            if isinstance(data, dict) and data.get("resultcount", 0) > 0:
                text = _("OK (bash resolved)")
            self.aur_result.setText(f"{text} \u00b7 {result['ms']:.0f} ms")
            self.aur_result.setStyleSheet(
                f"color: {Colors.GREEN}; font-size: {Fonts.SM};"
                f" font-weight: {Fonts.SEMI};"
                " border: none; background: transparent; padding: 8px 4px 4px 4px;")
        else:
            self.aur_result.setText(
                f"{_('Unreachable')} \u00b7 {result['ms']:.0f} ms"
                f" \u00b7 {result.get('err', '')[:80]}")
            self.aur_result.setStyleSheet(
                f"color: {Colors.RED}; font-size: {Fonts.SM};"
                f" font-weight: {Fonts.SEMI};"
                " border: none; background: transparent; padding: 8px 4px 4px 4px;")