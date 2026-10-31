import pytest
from PyQt6.QtWidgets import QApplication, QComboBox, QLabel

from neoarch.frontend.components.provider_chooser_dialog import (
    ProviderChooserDialog,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


CHOICES = [
    {"requested": "sh", "options": [
        {"name": "bash", "version": "5.3.20-1", "repo": "core"},
        {"name": "dash", "version": "0.5.12-3", "repo": "extra"},
    ]},
    {"requested": "ttf-font", "options": [
        {"name": "ttf-dejavu", "version": "2.37", "repo": "extra"},
        {"name": "ttf-liberation", "version": "2.1", "repo": "extra"},
    ]},
]


def test_dialog_defaults_to_first_provider(qapp):
    dlg = ProviderChooserDialog(None, CHOICES)
    assert dlg.selected() == ["bash", "ttf-dejavu"]
    texts = [lbl.text() for lbl in dlg.findChildren(QLabel)]
    assert "Provider for sh" in texts
    assert "Provider for ttf-font" in texts


def test_dialog_returns_chosen_providers(qapp):
    dlg = ProviderChooserDialog(None, CHOICES)
    combos = dlg.findChildren(QComboBox)
    assert len(combos) == 2
    combos[0].setCurrentIndex(1)
    combos[1].setCurrentIndex(1)
    assert dlg.selected() == ["dash", "ttf-liberation"]
