import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel

from neoarch.frontend.components.whats_new_dialog import (
    WhatIsNewDialog, _render_body, _rich,
)


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_rich_markdown_subset():
    out = _rich("**Bold** and `code` with [link](https://example.com)")
    assert "<b>Bold</b>" in out
    assert "<code>code</code>" in out
    assert '<a href="https://example.com">link</a>' in out


def test_render_body_handles_headings_bullets_and_blank_lines():
    out = _render_body("## Highlights\n- **Fast** checks\n\nDone")
    assert "Highlights" in out
    assert "<b>Fast</b>" in out
    assert "•" in out
    assert "Done" in out


def test_whats_new_dialog_matches_dialog_shell(qapp):
    blocks = [{"version": "3.4.5", "date": "2026-10-31",
               "sections": {"New Features": ["**Faster** checks"]}}]
    dlg = WhatIsNewDialog(blocks, current_version="3.4.5")
    assert dlg.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert dlg.continue_btn.text() == "Continue"
    assert dlg.minimumWidth() >= 560
    dlg.deleteLater()


def test_update_dialog_shows_release_body_and_actions(qapp):
    latest = {"version": "3.5.0", "body": "- Fixed `pipx` detection",
              "html_url": "https://example.com/release"}
    dlg = WhatIsNewDialog([], mode="update", latest=latest)
    assert dlg.update_btn.text() == "Update"
    assert dlg.skip_btn.text() == "Skip for now"
    labels = [w.text() for w in dlg.findChildren(QLabel)]
    assert any("RELEASE NOTES" in t for t in labels)
    dlg.deleteLater()
