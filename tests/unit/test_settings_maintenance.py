"""Smoke tests for the Maintenance settings page (card layout + actions)."""

import pytest
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton

from neoarch.frontend.views._settings_kit import Stepper
from neoarch.frontend.views.settings_maintenance import MaintenanceSettingsWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def _no_news_fetch(monkeypatch):
    """Never hit the RSS feed during widget construction."""
    monkeypatch.setattr(
        "neoarch.frontend.views.settings_maintenance.news_unseen_count",
        lambda: 0)


class _MsgBus:
    def __init__(self):
        self.messages = []

    def emit(self, *args):
        self.messages.append(args)


class _FakeApp(QWidget):
    """Minimal app the Maintenance settings page talks to."""

    def __init__(self):
        super().__init__()
        self.show_message = _MsgBus()
        self.orphans_clicked = 0
        self.pacnew_clicked = 0
        self.news_clicked = 0

    def cleanup_orphans(self):
        self.orphans_clicked += 1

    def manage_pacnew(self):
        self.pacnew_clicked += 1

    def show_arch_news(self):
        self.news_clicked += 1


def _labels(widget):
    return [lbl.text() for lbl in widget.findChildren(QLabel)]


def _buttons(widget):
    return {b.text(): b for b in widget.findChildren(QPushButton)}


def test_widget_constructs(qapp):
    w = MaintenanceSettingsWidget(_FakeApp())
    assert w.layout.count() >= 5
    w.deleteLater()


def test_page_has_expected_cards(qapp):
    w = MaintenanceSettingsWidget(_FakeApp())
    texts = set(_labels(w))
    for expected in (
        "Maintenance",
        "Orphaned Packages",
        "Config Files (.pacnew)",
        "Download Cache",
        "Arch Linux News",
    ):
        assert expected in texts, expected
    w.deleteLater()


def test_action_buttons_call_app(qapp):
    app = _FakeApp()
    w = MaintenanceSettingsWidget(app)
    buttons = _buttons(w)
    buttons["Remove Orphans"].click()
    buttons["Manage .pacnew"].click()
    assert app.orphans_clicked == 1
    assert app.pacnew_clicked == 1
    w.deleteLater()


def test_cache_stepper_present(qapp):
    w = MaintenanceSettingsWidget(_FakeApp())
    steppers = w.findChildren(Stepper)
    assert len(steppers) == 2
    assert steppers[0].value() == 3
    assert steppers[1].value() == 10
    w.deleteLater()


def test_news_button_connected(qapp):
    app = _FakeApp()
    w = MaintenanceSettingsWidget(app)
    buttons = _buttons(w)
    assert buttons["Show News"].click() is None  # clickable, wired
    assert app.news_clicked == 1
    w.deleteLater()


def test_mirrors_card_present(qapp):
    w = MaintenanceSettingsWidget(_FakeApp())
    texts = set(_labels(w))
    assert "Package Mirrors" in texts
    assert "Refresh mirror list" in texts
    assert "Latest mirrors" in texts
    assert "Refresh Mirrors" in _buttons(w)
    w.deleteLater()


def test_refresh_mirrors_without_reflector_reports(qapp, monkeypatch):
    import neoarch.backend.services.mirrors as mirrors

    monkeypatch.setattr(mirrors, "reflector_path", lambda: None)
    app = _FakeApp()
    w = MaintenanceSettingsWidget(app)
    _buttons(w)["Refresh Mirrors"].click()
    assert app.show_message.messages
    title, message = app.show_message.messages[-1]
    assert title == "Mirrors"
    assert "reflector" in message
    w.deleteLater()


def test_refresh_mirrors_reports_result(qapp, monkeypatch):
    import time
    import neoarch.backend.services.mirrors as mirrors

    monkeypatch.setattr(
        mirrors, "reflector_path", lambda: "/usr/bin/reflector")
    monkeypatch.setattr(
        mirrors, "refresh_mirrors", lambda latest=10: (True, "7"))
    app = _FakeApp()
    w = MaintenanceSettingsWidget(app)
    _buttons(w)["Refresh Mirrors"].click()
    deadline = time.time() + 2
    while not app.show_message.messages and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    assert app.show_message.messages
    title, message = app.show_message.messages[-1]
    assert title == "Mirrors"
    assert "7" in message
    w.deleteLater()
