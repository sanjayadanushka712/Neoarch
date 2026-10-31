"""Package groups browser page.

Lists every pacman group (read from the synced databases off the UI
thread), shows the group's packages with install state, and installs a
selection or the whole group through the normal installer pipeline.
"""

import threading

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QSplitter, QStyle, QStyleOptionViewItem, QStyledItemDelegate,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from neoarch.backend.services.groups import group_packages, list_groups
from neoarch.backend.services.i18n import _
from neoarch.frontend.components.toggle_switch import ToggleSwitch
from neoarch.frontend.components.updates_table import _UpdatesHeader
from neoarch.frontend.styles import Styles
from neoarch.frontend.tokens import Colors, Fonts, QSS, Radii

__all__ = ["GroupsTab"]


class _GroupCheckDelegate(QStyledItemDelegate):
    """Paint row checkboxes exactly like the Updates/Discover tables."""

    def __init__(self, tab, parent=None):
        super().__init__(parent)
        self._tab = tab

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt,
                          painter, opt.widget)

        entry = index.data(Qt.ItemDataRole.UserRole) or {}
        if not entry or entry.get("installed"):
            return
        checked = entry.get("name") in self._tab._checked
        size = 18
        rect = QRectF(
            option.rect.left() + (option.rect.width() - size) / 2,
            option.rect.top() + (option.rect.height() - size) / 2,
            size, size)
        _UpdatesHeader._draw_check(painter, rect, checked, False)


class GroupsTab(QWidget):
    """Full-page browser for pacman package groups."""

    groups_loaded = pyqtSignal(list)

    def __init__(self, main_app=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._groups = []
        self._entries = []
        self._checked = set()
        self._current_group = ""
        self._search_text = ""
        self._loading = False
        self._init_ui()
        self.groups_loaded.connect(self._on_loaded)
        if main_app is not None and hasattr(main_app, "installation_progress"):
            main_app.installation_progress.connect(self._on_install_progress)
        self.refresh()

    # ── UI ────────────────────────────────────────────────────────

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 12)
        root.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        # Left: group list
        left = QFrame()
        left.setObjectName("groupsListPanel")
        left.setStyleSheet(
            f"QFrame#groupsListPanel {{ background-color: {Colors.SURFACE};"
            f" border: 1px solid {Colors.BORDER};"
            f" border-radius: {Radii.LG}px; }}")
        left.setMinimumWidth(230)
        left.setMaximumWidth(340)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(_("Filter groups…"))
        self.filter_edit.setStyleSheet(QSS.LINEEDIT)
        self.filter_edit.textChanged.connect(self._filter_groups)
        left_layout.addWidget(self.filter_edit)

        self.group_list = QListWidget()
        self.group_list.setUniformItemSizes(True)
        self.group_list.setSpacing(2)
        self.group_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.group_list.currentItemChanged.connect(self._on_group_selected)
        left_layout.addWidget(self.group_list, 1)
        splitter.addWidget(left)

        # Right: group detail
        right = QFrame()
        right.setObjectName("groupsDetailPanel")
        right.setStyleSheet(
            f"QFrame#groupsDetailPanel {{ background-color: {Colors.SURFACE};"
            f" border: 1px solid {Colors.BORDER};"
            f" border-radius: {Radii.LG}px; }}")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        self.group_title = QLabel(_("Select a group"))
        self.group_title.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: 18px;"
            f" font-weight: {Fonts.SEMI}; background: transparent;"
            " border: none;")
        right_layout.addWidget(self.group_title)

        self.group_subtitle = QLabel("")
        self.group_subtitle.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.MD};"
            " background: transparent; border: none;")
        right_layout.addWidget(self.group_subtitle)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 4, 0, 0)
        controls.setSpacing(10)
        select_label = QLabel(_("Select all not installed"))
        select_label.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE};"
            " background: transparent; border: none;")
        controls.addWidget(select_label)
        self.select_all = ToggleSwitch(name="select-all-groups")
        self.select_all.toggled.connect(self._toggle_select_all)
        controls.addWidget(self.select_all)
        controls.addStretch(1)
        self.install_all_btn = QPushButton()
        self.install_all_btn.setMinimumHeight(36)
        self.install_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 8px 16px;
                font-size: {Fonts.BASE};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.06);
                border-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.10);
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_3};
                border-color: rgba(255, 255, 255, 0.06);
            }}
        """)
        self.install_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_all_btn.clicked.connect(self._install_whole_group)
        controls.addWidget(self.install_all_btn)
        self.install_btn = QPushButton()
        self.install_btn.setMinimumHeight(36)
        self.install_btn.setStyleSheet(
            Styles.btn_white(padding="8px 18px", size=Fonts.BASE,
                             radius=Radii.XL)
            + Styles.btn_white_disabled())
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.clicked.connect(self._install_selected)
        controls.addWidget(self.install_btn)
        right_layout.addLayout(controls)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["", _("Package"), _("Version"), _("Repository"), _("Status")])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 110)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setItemDelegateForColumn(
            0, _GroupCheckDelegate(self, self.table))
        self.table.cellClicked.connect(self._on_cell_clicked)
        right_layout.addWidget(self.table, 1)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 900])
        root.addWidget(splitter, 1)
        self._update_buttons()

    # ── data ──────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        if not self._groups and not self._loading:
            self.refresh()

    def refresh(self):
        if self._loading:
            return
        self._loading = True
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        try:
            groups = list_groups(refresh=True)
        except Exception:
            groups = []
        try:
            self.groups_loaded.emit(groups)
        except RuntimeError:
            pass

    def _on_loaded(self, groups):
        self._loading = False
        self._groups = groups or []
        previous = self._current_group
        self.group_list.blockSignals(True)
        self.group_list.clear()
        for group in self._groups:
            item = QListWidgetItem(
                f"{group['name']}  ({group['count']})")
            item.setData(Qt.ItemDataRole.UserRole, group["name"])
            item.setToolTip(
                _("{n} packages · {m} installed").format(
                    n=group["count"], m=group["installed"]))
            self.group_list.addItem(item)
        self.group_list.blockSignals(False)
        self._filter_groups(self.filter_edit.text())
        target = previous if previous else (
            self._groups[0]["name"] if self._groups else "")
        self._select_group(target)

    def _select_group(self, name):
        for row in range(self.group_list.count()):
            item = self.group_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == name:
                self.group_list.setCurrentItem(item)
                return
        first = self._first_visible_item()
        if first is not None:
            self.group_list.setCurrentItem(first)

    def _first_visible_item(self):
        for row in range(self.group_list.count()):
            item = self.group_list.item(row)
            if not item.isHidden():
                return item
        return None

    def _on_group_selected(self, current, _previous=None):
        if current is None:
            return
        name = current.data(Qt.ItemDataRole.UserRole) or ""
        self._current_group = name
        try:
            self._entries = group_packages(name)
        except Exception:
            self._entries = []
        self.group_title.setText(name)
        installed = sum(1 for entry in self._entries if entry["installed"])
        self.group_subtitle.setText(
            _("{n} packages · {m} installed").format(
                n=len(self._entries), m=installed))
        self._fill_table()
        self._update_buttons()

    def _fill_table(self):
        self._checked = set()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsEnabled)
            check.setData(Qt.ItemDataRole.UserRole, entry)
            self.table.setItem(row, 0, check)

            name_item = QTableWidgetItem(entry["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, entry)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(
                row, 2, QTableWidgetItem(entry.get("version", "")))
            self.table.setItem(
                row, 3, QTableWidgetItem(entry.get("repo", "")))

            status = QTableWidgetItem(
                _("Installed") if entry["installed"] else _("Available"))
            status.setForeground(QColor(
                Colors.GREEN if entry["installed"] else Colors.TEXT_3))
            self.table.setItem(row, 4, status)
        self.table.blockSignals(False)
        self.select_all.blockSignals(True)
        self.select_all.setChecked(False, animate=False)
        self.select_all.blockSignals(False)

    # ── filtering / selection ─────────────────────────────────────

    def set_search_text(self, text):
        """Filter the group list from the top navbar search box."""
        self._search_text = (text or "").strip().lower()
        self._filter_groups(self.filter_edit.text())

    def _filter_groups(self, text):
        needle = (text or "").strip().lower()
        navbar = self._search_text
        for row in range(self.group_list.count()):
            item = self.group_list.item(row)
            name = (item.data(Qt.ItemDataRole.UserRole) or "").lower()
            visible = ((not needle or needle in name)
                       and (not navbar or navbar in name))
            item.setHidden(not visible)
        current = self.group_list.currentItem()
        if current is None or current.isHidden():
            first = self._first_visible_item()
            if first is not None:
                self.group_list.setCurrentItem(first)
            else:
                self._current_group = ""
                self._entries = []
                self.group_title.setText(_("Select a group"))
                self.group_subtitle.setText("")
                self._fill_table()
                self._update_buttons()

    def _toggle_select_all(self, checked):
        if checked:
            self._checked = {entry["name"] for entry in self._entries
                             if not entry["installed"]}
        else:
            self._checked = set()
        self.table.viewport().update()
        self._update_buttons()

    def _on_cell_clicked(self, row, column):
        if column != 0:
            return
        item = self.table.item(row, 0)
        entry = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not entry or entry.get("installed"):
            return
        name = entry.get("name")
        if name in self._checked:
            self._checked.discard(name)
        else:
            self._checked.add(name)
        self.table.viewport().update()
        self._update_buttons()

    def _checked_names(self):
        return [entry["name"] for entry in self._entries
                if entry["name"] in self._checked
                and not entry["installed"]]

    def _update_buttons(self, *_args):
        selected = len(self._checked_names())
        self.install_btn.setText(
            _("Install Selected ({n})").format(n=selected))
        self.install_btn.setEnabled(selected > 0)
        pending = sum(1 for entry in self._entries if not entry["installed"])
        self.install_all_btn.setText(
            _("Install Whole Group ({n})").format(n=pending))
        self.install_all_btn.setEnabled(pending > 0)

    # ── install ───────────────────────────────────────────────────

    def _install_selected(self):
        self._install(self._checked_names())

    def _install_whole_group(self):
        names = [entry["name"] for entry in self._entries
                 if not entry["installed"]]
        self._install(names)

    def _install(self, names):
        if not names or self.main_app is None:
            return
        from neoarch.frontend.components.dark_dialogs import dark_confirm

        message = _("Install {n} package(s) from the {group} group?").format(
            n=len(names), group=self._current_group)
        if not dark_confirm(self, _("Install Packages"), message):
            return
        try:
            if not self.main_app.ensure_session_auth():
                return
        except Exception:
            return
        from neoarch.backend.package import installer
        installer.install_packages(self.main_app, {"pacman": names})

    def _on_install_progress(self, status, _can_cancel=False):
        try:
            if status == "start":
                self.setVisible(False)
            elif status in ("success", "failed", "cancelled"):
                QTimer.singleShot(900, self._after_install)
        except RuntimeError:
            pass  # widget destroyed during a UI rebuild

    def _after_install(self):
        try:
            if getattr(self.main_app, "current_view", "") == "groups":
                self.setVisible(True)
                self.refresh()
        except RuntimeError:
            pass
