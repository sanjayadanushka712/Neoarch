"""Pick which package satisfies a virtual dependency."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QWidget, QPushButton, QFrame,
)

from neoarch.frontend.tokens import Colors, Fonts
from neoarch.frontend.components.dark_dialogs import (
    _DIALOG_STYLE, _DialogTitleBar, _apply_dialog_flags,
    _BTN_PRIMARY, _BTN_SECONDARY,
)
from neoarch.backend.services.i18n import _


class ProviderChooserDialog(QDialog):
    """Ask the user which provider to install for each virtual dependency."""

    def __init__(self, parent, choices: list):
        super().__init__(parent)
        self.setWindowTitle(_("Choose providers"))
        self.setMinimumWidth(560)
        self.setStyleSheet(_DIALOG_STYLE)
        _apply_dialog_flags(self)

        self._combos = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_DialogTitleBar(_("Choose providers")))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 6, 24, 18)
        layout.setSpacing(14)

        subtitle = QLabel(
            _("Some dependencies can be satisfied by more than one package. "
              "Pick one for each."))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE};"
            " background: transparent; border: none;")
        layout.addWidget(subtitle)

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

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        rows = QVBoxLayout(inner)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.setSpacing(12)
        for choice in choices:
            rows.addWidget(self._choice_row(choice))
        rows.addStretch(1)
        scroll.setWidget(inner)
        scroll.setMaximumHeight(360)
        layout.addWidget(scroll)

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
        cont = QPushButton(_("Continue"))
        cont.setStyleSheet(_BTN_PRIMARY)
        cont.clicked.connect(self.accept)
        btn_row.addWidget(cont)
        layout.addLayout(btn_row)

        root.addWidget(content)
        cont.setFocus()

    def _choice_row(self, choice: dict) -> QWidget:
        box = QWidget()
        box.setObjectName("choiceRow")
        box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        box.setStyleSheet(
            f"#choiceRow {{ background: {Colors.SURFACE_2};"
            f" border: 1px solid {Colors.BORDER}; border-radius: 10px; }}")
        outer = QVBoxLayout(box)
        outer.setContentsMargins(14, 10, 14, 12)
        outer.setSpacing(6)

        title = QLabel(_("Provider for {name}").format(
            name=choice.get("requested", "")))
        title.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.BASE}; font-weight: 600;"
            " background: transparent; border: none;")
        outer.addWidget(title)

        combo = QComboBox()
        for option in choice.get("options") or []:
            label = option.get("name", "")
            version = option.get("version", "")
            repo = option.get("repo", "")
            extra = " · ".join(part for part in (version, repo) if part)
            if extra:
                label = f"{label}   {extra}"
            combo.addItem(label, userData=option.get("name", ""))
        outer.addWidget(combo)
        self._combos.append(combo)
        return box

    def selected(self) -> list:
        """One chosen package name per provider question, in order."""
        return [combo.currentData() for combo in self._combos]


def show_provider_choices(parent, choices: list):
    """Show the chooser.

    Returns the list of chosen provider names, or ``None`` when cancelled.
    """
    dlg = ProviderChooserDialog(parent, choices)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return dlg.selected()
