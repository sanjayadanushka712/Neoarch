import pytest
from PyQt6.QtWidgets import QApplication, QLabel

from neoarch.frontend.components.about_tab import _ReleaseNotesTab


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_release_notes_tab_uses_curated_changelog(qapp):
    tab = _ReleaseNotesTab()
    labels = [w.text() for w in tab.findChildren(QLabel)]
    assert any("Upcoming release" in t for t in labels)
    assert any("Version 3.4.5" in t for t in labels)
    assert any("New Features" in t for t in labels)
    tab.deleteLater()
