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


def test_release_url_keeps_legacy_v_prefix():
    from neoarch.frontend.components import about_tab

    assert about_tab._release_url("3.4.5").endswith("/v3.4.5")
    assert about_tab._release_url("3.5.0").endswith("/3.5.0")


def test_git_tags_fall_back_to_changelog(monkeypatch):
    from neoarch.frontend.components import about_tab

    monkeypatch.setattr(about_tab, "_run_cmd", lambda *a, **k: None)
    tags = about_tab._git_tags()
    assert tags
    assert "Unreleased" not in tags


def test_git_log_count_is_unknown_without_git(monkeypatch):
    from neoarch.frontend.components import about_tab

    monkeypatch.setattr(about_tab, "_run_cmd", lambda *a, **k: None)
    assert about_tab._git_log_count() is None
