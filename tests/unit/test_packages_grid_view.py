"""Grid card click/checkbox behavior."""

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication
import pytest

from neoarch.frontend.components.packages_grid_view import PackageCard


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_card_body_click_opens_without_toggling_checkbox(qapp):
    card = PackageCard({"name": "bash", "source": "pacman"}, 0, None)
    card.resize(card.CARD_W, card.CARD_H)
    QApplication.instance().processEvents()
    clicks = []
    card.clicked.connect(lambda row, pkg: clicks.append(pkg["name"]))

    ev = QMouseEvent(QMouseEvent.Type.MouseButtonRelease,
                     QPointF(60, 60), QPointF(60, 60),
                     Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier)
    card.mouseReleaseEvent(ev)

    assert clicks == ["bash"]
    assert card.checkbox.isChecked() is False


def test_checkbox_click_toggles_and_does_not_double_fire_card_click(qapp):
    card = PackageCard({"name": "ripgrep", "source": "pacman"}, 0, None)
    card.resize(card.CARD_W, card.CARD_H)
    QApplication.instance().processEvents()
    clicks = []
    toggled = []
    card.clicked.connect(lambda row, pkg: clicks.append(pkg["name"]))
    card.toggled.connect(lambda row, state: toggled.append((row, state)))
    card.checkbox.setChecked(False)

    # Toggle through the checkbox's own widget path.
    card.checkbox.toggle()

    assert toggled == [(0, True)]
    assert clicks == []
    assert card.checkbox.isChecked() is True
