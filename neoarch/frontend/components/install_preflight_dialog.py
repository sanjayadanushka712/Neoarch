"""Install preflight summary dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget,
    QPushButton, QFrame,
)

from neoarch.frontend.tokens import Colors, Fonts
from neoarch.frontend.components.dark_dialogs import (
    _DIALOG_STYLE, _DialogTitleBar, _apply_dialog_flags,
    _BTN_PRIMARY, _BTN_SECONDARY,
)
from neoarch.frontend.components.toggle_switch import ToggleSwitch
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


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(
        f"color: {Colors.TEXT_2}; font-size: {Fonts.SM}; font-weight: 600;"
        " background: transparent; border: none;")
    return label


def _stat(label: str, value: str, color: str) -> QWidget:
    box = QWidget()
    box.setObjectName("statCard")
    box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    box.setStyleSheet(
        "#statCard { background: rgba(255,255,255,0.04);"
        f" border: 1px solid {Colors.BORDER}; border-radius: 10px; }}")
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


def _card() -> tuple:
    """Scrollable card that holds a list of rows."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(
        "QScrollArea { background: transparent; border: none; }"
        "QScrollBar:vertical { background: transparent; width: 8px;"
        " margin: 4px 0; }"
        f"QScrollBar::handle:vertical {{ background: {Colors.BORDER};"
        " border-radius: 4px; min-height: 24px; }"
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical"
        " { height: 0; }")

    card = QWidget()
    card.setObjectName("listCard")
    card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    card.setStyleSheet(
        f"#listCard {{ background: {Colors.SURFACE_2};"
        f" border: 1px solid {Colors.BORDER}; border-radius: 10px; }}")
    rows = QVBoxLayout(card)
    rows.setContentsMargins(6, 6, 6, 6)
    rows.setSpacing(0)
    scroll.setWidget(card)
    return scroll, rows


class InstallPreflightDialog(QDialog):
    """Summarises the resolved transaction before installing."""

    def __init__(self, parent, plan: dict):
        super().__init__(parent)
        self.setWindowTitle(_("Install Summary"))
        self.setMinimumWidth(620)
        self.setStyleSheet(_DIALOG_STYLE)
        _apply_dialog_flags(self)

        packages = plan.get("packages") or []
        optional = plan.get("optional") or []
        self._toggles = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_DialogTitleBar(_("Install Summary")))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(26, 6, 26, 20)
        layout.setSpacing(14)

        subtitle = QLabel(
            _("{count} package{s} will be installed").format(
                count=len(packages), s="" if len(packages) == 1 else "s"))
        subtitle.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.BASE};"
            " background: transparent; border: none;")
        layout.addWidget(subtitle)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        stats.addWidget(_stat(_("Download size"),
                              _fmt_size(plan.get("total_download")),
                              Colors.ACCENT), 1)
        stats.addWidget(_stat(_("Installed size"),
                              _fmt_size(plan.get("total_installed")),
                              Colors.TEAL), 1)
        layout.addLayout(stats)

        layout.addWidget(_caption(_("Packages to install")))
        scroll, rows = _card()
        scroll.setMaximumHeight(240)
        for pkg in packages:
            rows.addWidget(self._row(pkg))
        rows.addStretch(1)
        layout.addWidget(scroll)

        if optional:
            layout.addWidget(self._optional_section(optional))

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(
            "background: rgba(255,255,255,0.08); border: none;")
        layout.addWidget(divider)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
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

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(_caption(_("Optional dependencies")))
        header.addStretch()
        hint = QLabel(_("Select optional dependencies to install as well"))
        hint.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
            " background: transparent; border: none;")
        header.addWidget(hint)
        outer.addLayout(header)

        scroll, rows = _card()
        scroll.setMaximumHeight(172)
        for i, dep in enumerate(optional):
            rows.addWidget(self._optional_row(dep, last=i == len(optional) - 1))
        rows.addStretch(1)
        outer.addWidget(scroll)
        return box

    def _optional_row(self, dep: dict, last: bool = False) -> QWidget:
        name = dep.get("name", "")
        desc = dep.get("description", "")

        row = QWidget()
        row.setObjectName("depRow")
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        border = "" if last else " border-bottom: 1px solid rgba(255,255,255,0.06);"
        row.setStyleSheet(
            f"#depRow {{ background: transparent; border: none;{border}"
            " border-radius: 6px; }"
            f"#depRow:hover {{ background: rgba(255,255,255,0.04); }}")

        hl = QHBoxLayout(row)
        hl.setContentsMargins(12, 7, 10, 7)
        hl.setSpacing(14)
        hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        texts = QVBoxLayout()
        texts.setSpacing(1)
        title = QLabel(name)
        title.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.BASE};"
            f" font-weight: {Fonts.MEDIUM};"
            " background: transparent; border: none;")
        texts.addWidget(title)
        if desc:
            sub = QLabel(desc)
            sub.setWordWrap(True)
            sub.setStyleSheet(
                f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
                " background: transparent; border: none;")
            texts.addWidget(sub)
        hl.addLayout(texts, 1)

        toggle = ToggleSwitch(row, name)
        toggle.setProperty("dep_name", name)
        toggle.setToolTip(desc or name)
        self._toggles.append(toggle)
        hl.addWidget(toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

    def selected_optional(self) -> list:
        """Names of optional dependencies the user enabled."""
        return [t.property("dep_name") for t in self._toggles if t.isChecked()]

    @staticmethod
    def _row(pkg: dict) -> QWidget:
        row = QWidget()
        row.setObjectName("pkgRow")
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row.setStyleSheet(
            "#pkgRow { background: transparent; border: none;"
            " border-bottom: 1px solid rgba(255,255,255,0.06);"
            " border-radius: 6px; }"
            "#pkgRow:hover { background: rgba(255,255,255,0.04); }")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(12, 8, 12, 8)
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
