"""Per-package transaction history dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget,
    QPushButton, QFrame,
)

from neoarch.frontend.tokens import Colors, Fonts
from neoarch.frontend.components.dark_dialogs import (
    _DIALOG_STYLE, _DialogTitleBar, _apply_dialog_flags, _BTN_SECONDARY,
)
from neoarch.backend.services.i18n import _

_ACTION_COLORS = {
    "install": Colors.GREEN,
    "upgrade": Colors.ACCENT,
    "downgrade": Colors.YELLOW,
    "reinstall": Colors.BLUE,
    "remove": Colors.RED,
}

_ACTION_LABELS = {
    "install": "Installed",
    "upgrade": "Upgraded",
    "downgrade": "Downgraded",
    "reinstall": "Reinstalled",
    "remove": "Removed",
}


def _format_date(timestamp) -> str:
    if timestamp is None:
        return "—"
    try:
        return timestamp.strftime("%b %d, %Y · %H:%M")
    except Exception:
        return "—"


def _history_rows(entries) -> list:
    """Flatten transactions into (timestamp, event) pairs, newest first."""
    rows = []
    for entry in entries or []:
        for event in entry.get("packages") or []:
            rows.append((entry.get("timestamp"), event))
    return rows


class PackageHistoryDialog(QDialog):
    """Lists every pacman transaction that touched one package."""

    def __init__(self, parent, name: str, entries):
        super().__init__(parent)
        self.setWindowTitle(_("History"))
        self.setMinimumWidth(540)
        self.setStyleSheet(_DIALOG_STYLE)
        _apply_dialog_flags(self)

        rows = _history_rows(entries)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_DialogTitleBar(_("History")))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 4, 24, 18)
        layout.setSpacing(12)

        title = QLabel(name)
        title.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.HERO};"
            " font-weight: 700; background: transparent; border: none;"
        )
        layout.addWidget(title)

        count = len(rows)
        subtitle = QLabel(
            _("{count} transaction{s}").format(
                count=count, s="" if count == 1 else "s"))
        subtitle.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
            " background: transparent; border: none;"
        )
        layout.addWidget(subtitle)

        if rows:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet(
                f"QScrollArea {{ background: {Colors.SURFACE_2};"
                f" border: 1px solid {Colors.BORDER}; border-radius: 10px; }}")
            scroll.setMaximumHeight(360)

            inner = QWidget()
            inner.setStyleSheet("background: transparent;")
            rows_layout = QVBoxLayout(inner)
            rows_layout.setContentsMargins(4, 4, 4, 4)
            rows_layout.setSpacing(0)
            for timestamp, event in rows:
                rows_layout.addWidget(self._row(timestamp, event))
            rows_layout.addStretch(1)
            scroll.setWidget(inner)
            layout.addWidget(scroll)
        else:
            empty = QLabel(_("No transactions for this package yet."))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {Colors.TEXT_3}; font-size: {Fonts.MD};"
                f" background: {Colors.SURFACE_2};"
                f" border: 1px solid {Colors.BORDER}; border-radius: 10px;"
                " padding: 28px 12px;"
            )
            layout.addWidget(empty)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close = QPushButton(_("Close"))
        close.setStyleSheet(_BTN_SECONDARY)
        close.clicked.connect(self.accept)
        btn_row.addWidget(close)
        layout.addLayout(btn_row)

        root.addWidget(content)
        close.setFocus()

    @staticmethod
    def _row(timestamp, event) -> QWidget:
        action = event.get("action", "")
        version = event.get("version", "")
        old_version = event.get("old_version", "")
        color = _ACTION_COLORS.get(action, Colors.TEXT_2)
        label = _(_ACTION_LABELS.get(action, action))

        row = QWidget()
        row.setStyleSheet(
            "background: transparent;"
            " border-bottom: 1px solid rgba(255,255,255,0.06);")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.setSpacing(12)

        date = QLabel(_format_date(timestamp))
        date.setFixedWidth(150)
        date.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
            " background: transparent; border: none;")
        hl.addWidget(date)

        action_lbl = QLabel(label)
        action_lbl.setFixedWidth(96)
        action_lbl.setStyleSheet(
            f"color: {color}; font-size: {Fonts.SM}; font-weight: 700;"
            " background: transparent; border: none;")
        hl.addWidget(action_lbl)

        text = f"{old_version}  →  {version}" if old_version else version
        version_lbl = QLabel(text)
        version_lbl.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.MD};"
            " background: transparent; border: none;")
        hl.addWidget(version_lbl, 1)
        return row


def show_package_history(parent, name: str, entries) -> None:
    """Open the per-package history dialog (blocking)."""
    PackageHistoryDialog(parent, name, entries).exec()
