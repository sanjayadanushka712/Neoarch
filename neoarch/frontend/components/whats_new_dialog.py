"""What's New dialog — shows descriptive, card-wise release notes.

Rendered from the curated ``CHANGELOG.md`` (see the release-notes service) so
installed users always see exactly what was added and fixed, even without a
git checkout or network access.

Two modes:

* ``whats_new`` — shown once after the app itself has been updated.
* ``update``   — shown when a newer GitHub release is available; includes the
  release summary and an Update button that opens the GitHub release page.
"""

import html
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame,
)

from neoarch.frontend.tokens import Colors, Fonts, Radii
from neoarch.frontend.styles import Styles
from neoarch.frontend.components.dark_dialogs import (
    _DIALOG_STYLE, _DialogTitleBar, _apply_dialog_flags,
)
from neoarch.backend.services.i18n import _
from neoarch.backend.services.release_notes import latest_release, SECTION_LABELS


def _open_url(url):
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import QUrl
    QDesktopServices.openUrl(QUrl(url))


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_CODE_RE = re.compile(r"`(.+?)`")
_LINK_RE = re.compile(r"\[(.+?)\]\((https?://[^)]+)\)")


def _rich(text):
    """Escape then render the small markdown subset used in the changelog."""
    out = html.escape(text, quote=False)
    out = _BOLD_RE.sub(r"<b>\1</b>", out)
    out = _CODE_RE.sub(r"<code>\1</code>", out)
    out = _LINK_RE.sub(
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">'
                  f"{m.group(1)}</a>",
        out)
    return out


def _render_body(text):
    """Render a GitHub release body as lightweight rich text."""
    lines = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            lines.append("<div style='height: 5px'></div>")
            continue
        if line.startswith("#"):
            lines.append(
                f"<div style='margin-top: 6px'><b>{_rich(line.lstrip('# '))}"
                "</b></div>")
            continue
        if line.startswith(("- ", "* ")):
            lines.append(f"<div>•&nbsp; {_rich(line[2:])}</div>")
            continue
        lines.append(f"<div>{_rich(line)}</div>")
    return "".join(lines)


class WhatIsNewDialog(QDialog):
    """Modal card-based release notes dialog."""

    def __init__(self, blocks, mode="whats_new", latest=None,
                 current_version="", parent=None):
        super().__init__(parent)
        self._blocks = blocks or []
        self._mode = mode
        self._latest = latest or {}
        self._current_version = current_version
        self.setWindowTitle(_("What's New"))
        self.resize(720, 640)
        self.setMinimumSize(560, 420)
        self.setStyleSheet(_DIALOG_STYLE)
        _apply_dialog_flags(self)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_DialogTitleBar(_("What's New")))

        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(28, 6, 28, 22)
        v.setSpacing(16)

        if self._mode == "update" and self._latest:
            version = self._latest.get("version", "")
            title = _("NeoArch {version} is available").format(version=version)
            subtitle = _("A new version of NeoArch is available")
        else:
            version = self._current_version
            title = _("What's New in NeoArch {version}").format(version=version)
            subtitle = _("Here's what's new in this update")

        v.addLayout(self._heading(version, title, subtitle))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(Styles.scrollbar())
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(inner)
        cl.setContentsMargins(0, 0, 6, 0)
        cl.setSpacing(14)

        body = self._latest.get("body") if self._mode == "update" else ""
        if body:
            cl.addWidget(self._release_body_card(body))
        for block in self._blocks:
            cl.addWidget(self._block_card(block))
        cl.addStretch(1)
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)

        v.addLayout(self._actions())
        root.addWidget(content, 1)

    def _heading(self, version, title, subtitle):
        row = QHBoxLayout()
        row.setSpacing(14)

        col = QVBoxLayout()
        col.setSpacing(7)
        if version:
            chip = QLabel(f"v{version}")
            chip.setStyleSheet(
                f"background: {Colors.ACCENT_SOFT};"
                f" color: {Colors.ACCENT};"
                f" border: 1px solid {Colors.ACCENT_BORDER};"
                f" border-radius: {Radii.FULL}px;"
                f" padding: 3px 10px; font-size: {Fonts.SM};"
                f" font-weight: {Fonts.SEMI};")
            col.addWidget(chip, 0, Qt.AlignmentFlag.AlignLeft)

        lbl = QLabel(title)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.DISPLAY};"
            f" font-weight: {Fonts.BOLD}; letter-spacing: -0.4px;"
            " background: transparent; border: none;")
        col.addWidget(lbl)

        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE};"
            " background: transparent; border: none;")
        col.addWidget(sub)

        row.addLayout(col, 1)
        return row

    def _card(self, bg=Colors.SURFACE):
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setStyleSheet(Styles.card(bg=bg))
        return card

    def _release_body_card(self, body):
        card = self._card(Colors.SURFACE_2)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 18)
        cl.setSpacing(10)

        head = QLabel(_("Release Notes").upper())
        head.setStyleSheet(
            f"color: {Colors.ACCENT}; font-size: {Fonts.XS};"
            f" font-weight: {Fonts.SEMI}; letter-spacing: 0.8px;"
            " background: transparent; border: none;")
        cl.addWidget(head)

        text = QLabel(_render_body(body))
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setWordWrap(True)
        text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        text.setOpenExternalLinks(True)
        text.setStyleSheet(
            f"color: {Colors.TEXT_2}; font-size: {Fonts.BASE};"
            " background: transparent; border: none;")
        cl.addWidget(text)
        return card

    def _block_card(self, block):
        card = self._card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 18)
        cl.setSpacing(12)

        version = block.get("version", "")
        if version.lower() == "unreleased":
            version_text = _("Upcoming release")
        else:
            version_text = _("Version {version}").format(version=version)

        head = QHBoxLayout()
        head.setSpacing(10)
        version_lbl = QLabel(version_text)
        version_lbl.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: {Fonts.CARD_TITLE};"
            f" font-weight: {Fonts.SEMI}; background: transparent;"
            " border: none;")
        head.addWidget(version_lbl)
        head.addStretch(1)
        date = block.get("date", "")
        if date:
            date_lbl = QLabel(date)
            date_lbl.setStyleSheet(
                f"color: {Colors.TEXT_3}; font-size: {Fonts.SM};"
                " background: transparent; border: none;")
            head.addWidget(date_lbl)
        cl.addLayout(head)

        sections = block.get("sections", {})
        for label in SECTION_LABELS:
            items = sections.get(label)
            if not items:
                continue
            cl.addWidget(self._section_block(label, items))

        return card

    def _section_block(self, label, items):
        box = QWidget()
        box.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(0, 2, 0, 0)
        bl.setSpacing(7)

        head = QLabel(_(label).upper())
        head.setStyleSheet(
            f"color: {Colors.TEXT_3}; font-size: {Fonts.XS};"
            f" font-weight: {Fonts.SEMI}; letter-spacing: 0.8px;"
            " background: transparent; border: none;")
        bl.addWidget(head)

        for item in items:
            row = QHBoxLayout()
            row.setSpacing(9)
            dot = QLabel("•")
            dot.setStyleSheet(
                f"color: {Colors.ACCENT}; font-size: {Fonts.BASE};"
                " background: transparent; border: none;")
            dot.setFixedWidth(10)
            row.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            text = QLabel(_rich(item))
            text.setTextFormat(Qt.TextFormat.RichText)
            text.setWordWrap(True)
            text.setStyleSheet(
                f"font-size: {Fonts.BASE}; color: {Colors.TEXT_2};"
                " background: transparent; border: none;")
            row.addWidget(text, 1)
            bl.addLayout(row)

        return box

    def _actions(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch(1)

        if self._mode == "update" and self._latest:
            self.skip_btn = QPushButton(_("Skip for now"))
            self.skip_btn.setMinimumHeight(38)
            self.skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.skip_btn.setStyleSheet(Styles.btn_secondary())
            self.skip_btn.clicked.connect(self.accept)
            row.addWidget(self.skip_btn)

            self.update_btn = QPushButton(_("Update"))
            self.update_btn.setMinimumHeight(38)
            self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.update_btn.setDefault(True)
            self.update_btn.setStyleSheet(Styles.btn_white())
            self.update_btn.clicked.connect(
                lambda: _open_url(self._latest.get("html_url", "")))
            row.addWidget(self.update_btn)
        else:
            self.continue_btn = QPushButton(_("Continue"))
            self.continue_btn.setMinimumHeight(38)
            self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.continue_btn.setDefault(True)
            self.continue_btn.setStyleSheet(Styles.btn_white())
            self.continue_btn.clicked.connect(self.accept)
            row.addWidget(self.continue_btn)

        return row


def show_whats_new(parent, blocks, current_version=""):
    """Blocking What's New dialog after an update."""
    dialog = WhatIsNewDialog(blocks, mode="whats_new",
                             current_version=current_version, parent=parent)
    dialog.exec()


def show_update_available(parent, latest, blocks):
    """Blocking 'update available' dialog with the release summary."""
    dialog = WhatIsNewDialog(blocks, mode="update", latest=latest,
                             parent=parent)
    dialog.exec()


def fetch_latest_release():
    """Best-effort latest GitHub release (background-friendly)."""
    return latest_release()
