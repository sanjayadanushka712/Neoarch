"""Install preflight summary dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QWidget, QPushButton, QFrame,
)

from neoarch.frontend.tokens import Colors, Fonts
from neoarch.frontend.components.dark_dialogs import (
    _DIALOG_STYLE, _DialogTitleBar, _apply_dialog_flags,
    _BTN_PRIMARY, _BTN_SECONDARY,
)
from neoarch.backend.services.i18n import _


def _fmt_size(size) -> str:
    if not size:
        return "—"
    size = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GiB"


def _stat(label: str, value: str, color: str) -> QWidget:
    box = QWidget()
    box.setStyleSheet(
        f"background: rgba(255,255,255,0.04);"
        f" border: 1px solid {Colors.BORDER}; border-radius: 10px;")
    v = QVBoxLayout(box)
    v.setContentsMargins(14, 10, 14, 10)
    v.setSpacing(2)

    cap = QLabel(label)
    cap.setStyleSheet(
        f"color: {Colors.TEXT_3}; font-size: {Fonts.SM}; font-weight: 600;"
        " background: transparent; border: none;")
    v.addWidget(cap)

    val = QLabel(value)
    val.setStyleSheet(
        f"color: {color}; font-size: {Fonts.HERO}; font-weight: 700;"
        " background: transparent; border: none;")
    v.addWidget(val)
    return box


class InstallPreflightDialog(QDialog):
    """Summarises the resolved pacman transaction before installing."""

    def __init__(self, parent, plan: dict):
        super().__init__(parent)
        self.setWindowTitle(_("Install Summary"))
        self.setMinimumWidth(560)
        self.setStyleSheet(_DIALOG_STYLE)
        _apply_dialog_flags(self)

        packages = plan.get("packages") or []
        optional = plan.get("optional") or []
        self._checks = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_DialogTitleBar(_("Install Summary")))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 4, 24, 18)
        layout.setSpacing(12)

        subtitle = QLabel(
            _("{count} package{s} will be installed").format(
                count=len(packages), s="" if len(packages) == 1 else "s"))
        subtitle.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.BASE};"
            " background: transparent; border: none;")
        layout.addWidget(subtitle)

        stats = QHBoxLayout()
        stats.setSpacing(8)
        stats.addWidget(_stat(_("Download size"),
                              _fmt_size(plan.get("total_download")),
                              Colors.ACCENT), 1)
        stats.addWidget(_stat(_("Installed size"),
                              _fmt_size(plan.get("total_installed")),
                              Colors.TEAL), 1)
        layout.addLayout(stats)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {Colors.SURFACE_2};"
            f" border: 1px solid {Colors.BORDER}; border-radius: 10px; }}")
        scroll.setMaximumHeight(260)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        rows = QVBoxLayout(inner)
        rows.setContentsMargins(4, 4, 4, 4)
        rows.setSpacing(0)
        for pkg in packages:
            rows.addWidget(self._row(pkg))
        rows.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        if optional:
            layout.addWidget(self._optional_section(optional))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton(_("Cancel"))
        cancel.setStyleSheet(_BTN_SECONDARY)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        install = QPushButton(_("Install"))
        install.setStyleSheet(_BTN_PRIMARY)
        install.clicked.connect(self.accept)
        btn_row.addWidget(install)
        layout.addLayout(btn_row)

        root.addWidget(content)
        install.setFocus()

    def _optional_section(self, optional: list) -> QWidget:
        box = QWidget()
        box.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        title = QLabel(_("Optional dependencies"))
        title.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.BASE}; font-weight: 600;"
            " background: transparent; border: none;")
        outer.addWidget(title)

        hint = QLabel(_("Select optional dependencies to install as well"))
        hint.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
            " background: transparent; border: none;")
        outer.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {Colors.SURFACE_2};"
            f" border: 1px solid {Colors.BORDER}; border-radius: 10px; }}")
        scroll.setMaximumHeight(150)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        rows = QVBoxLayout(inner)
        rows.setContentsMargins(10, 6, 10, 6)
        rows.setSpacing(2)
        for dep in optional:
            name = dep.get("name", "")
            desc = dep.get("description", "")
            text = f"{name} — {desc}" if desc else name
            check = QCheckBox(text)
            check.setProperty("dep_name", name)
            check.setToolTip(desc or name)
            check.setStyleSheet(
                f"QCheckBox {{ color: {Colors.TEXT_2};"
                f" font-size: {Fonts.SM}; background: transparent;"
                " border: none; spacing: 8px; }"
                f"QCheckBox:hover {{ color: {Colors.TEXT}; }}"
                f"QCheckBox::indicator {{ width: 16px; height: 16px;"
                f" border: 1px solid {Colors.BORDER}; border-radius: 4px;"
                f" background: {Colors.SURFACE}; }}"
                f"QCheckBox::indicator:checked {{ background: {Colors.ACCENT};"
                f" border-color: {Colors.ACCENT}; }}")
            self._checks.append(check)
            rows.addWidget(check)
        rows.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return box

    def selected_optional(self) -> list:
        """Names of optional dependencies the user ticked."""
        return [c.property("dep_name") for c in self._checks if c.isChecked()]

    @staticmethod
    def _row(pkg: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet(
            "background: transparent;"
            " border-bottom: 1px solid rgba(255,255,255,0.06);")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(10, 7, 10, 7)
        hl.setSpacing(8)

        name = QLabel(pkg.get("name", ""))
        name.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.MD}; font-weight: 600;"
            " background: transparent; border: none;")
        hl.addWidget(name)

        version = QLabel(pkg.get("version", ""))
        version.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
            " background: transparent; border: none;")
        hl.addWidget(version)

        repo = QLabel(pkg.get("repo", ""))
        repo.setStyleSheet(
            f"color: {Colors.ACCENT}; font-size: {Fonts.XS}; font-weight: 700;"
            " background: transparent; border: none;")
        hl.addWidget(repo)
        hl.addStretch(1)

        size = QLabel(_fmt_size(pkg.get("download_size")))
        size.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.SM};"
            " background: transparent; border: none;")
        hl.addWidget(size)
        return row


def show_install_plan(parent, plan: dict):
    """Show the summary.

    Returns the list of selected optional dependencies when the user accepts
    the install, or ``None`` when the dialog is cancelled.
    """
    dlg = InstallPreflightDialog(parent, plan)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return dlg.selected_optional()
