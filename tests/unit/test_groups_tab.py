"""Tests for the Groups settings-free browser page."""

import time

import pytest
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget

import neoarch.backend.package.installer as installer
import neoarch.frontend.components.dark_dialogs as dark_dialogs
import neoarch.frontend.components.groups_tab as groups_tab


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


GROUPS = [
    {"name": "editors", "count": 2, "installed": 1},
    {"name": "shells", "count": 2, "installed": 0},
]
PACKAGES = {
    "editors": [
        {"name": "vim", "version": "9.1-1", "repo": "extra",
         "installed": True},
        {"name": "neovim", "version": "0.10-1", "repo": "extra",
         "installed": False},
    ],
    "shells": [
        {"name": "bash", "version": "5.2-1", "repo": "core",
         "installed": False},
        {"name": "zsh", "version": "5.9-1", "repo": "core",
         "installed": False},
    ],
}


class _MsgBus:
    def __init__(self):
        self.messages = []

    def emit(self, *args):
        self.messages.append(args)


class _FakeApp(QWidget):
    installation_progress = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self.current_view = "groups"
        self.show_message = _MsgBus()
        self.authenticated = True

    def ensure_session_auth(self):
        return self.authenticated


@pytest.fixture(autouse=True)
def _stub_backend(monkeypatch):
    monkeypatch.setattr(groups_tab, "list_groups",
                        lambda refresh=False: list(GROUPS))
    monkeypatch.setattr(groups_tab, "group_packages",
                        lambda name: list(PACKAGES.get(name, [])))


def _wait(qapp, cond, timeout=2.0):
    deadline = time.time() + timeout
    while not cond() and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    return cond()


def _make_tab(qapp):
    app = _FakeApp()
    tab = groups_tab.GroupsTab(app)
    assert _wait(qapp, lambda: tab.group_list.count() == 2)
    return app, tab


def test_lists_groups_and_selects_first(qapp):
    _app, tab = _make_tab(qapp)
    assert tab.group_list.count() == 2
    assert tab._current_group == "editors"
    assert tab.table.rowCount() == 2
    assert tab.group_title.text() == "editors"
    assert tab.install_all_btn.text() == "Install Whole Group (1)"
    assert not tab.install_btn.isEnabled()
    tab.deleteLater()


def test_checking_rows_updates_buttons(qapp):
    _app, tab = _make_tab(qapp)
    check = tab.table.item(1, 0)
    check.setCheckState(check.checkState().Checked)
    assert tab.install_btn.text() == "Install Selected (1)"
    assert tab.install_btn.isEnabled()
    tab.deleteLater()


def test_installed_rows_are_not_checkable(qapp):
    _app, tab = _make_tab(qapp)
    installed = tab.table.item(0, 0)
    assert not (installed.flags() & installed.flags().ItemIsUserCheckable)
    tab.deleteLater()


def test_select_all_toggles_available_rows(qapp):
    _app, tab = _make_tab(qapp)
    tab.select_all.setChecked(True)
    assert tab.install_btn.text() == "Install Selected (1)"
    tab.group_list.setCurrentRow(1)
    qapp.processEvents()
    tab.select_all.setChecked(True)
    assert tab.install_btn.text() == "Install Selected (2)"
    tab.deleteLater()


def test_navbar_search_filters_groups(qapp):
    _app, tab = _make_tab(qapp)
    tab.set_search_text("shell")
    hidden = [tab.group_list.item(i).isHidden()
              for i in range(tab.group_list.count())]
    assert hidden == [True, False]
    assert tab._current_group == "shells"
    tab.deleteLater()


def test_install_selected_confirms_and_calls_installer(
        qapp, monkeypatch):
    _app, tab = _make_tab(qapp)
    calls = {}
    monkeypatch.setattr(dark_dialogs, "dark_confirm",
                        lambda *a, **k: True)
    monkeypatch.setattr(
        installer, "install_packages",
        lambda app, payload: calls.update(payload=payload))
    tab.table.item(1, 0).setCheckState(
        tab.table.item(1, 0).checkState().Checked)
    tab._install_selected()
    assert calls["payload"] == {"pacman": ["neovim"]}
    tab.deleteLater()


def test_install_cancelled_does_not_call_installer(
        qapp, monkeypatch):
    _app, tab = _make_tab(qapp)
    monkeypatch.setattr(dark_dialogs, "dark_confirm",
                        lambda *a, **k: False)
    monkeypatch.setattr(
        installer, "install_packages",
        lambda app, payload: pytest.fail("should not install"))
    tab._install_whole_group()
    tab.deleteLater()


def test_install_hides_page_during_progress(qapp):
    app, tab = _make_tab(qapp)
    app.installation_progress.emit("start", False)
    qapp.processEvents()
    assert tab.isVisible() is False or tab.isHidden()
    tab.deleteLater()
