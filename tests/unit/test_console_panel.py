"""Console strip behaviour: soft-wrap is enabled by default and persisted."""

import pytest
from PyQt6.QtWidgets import QApplication, QTextEdit

from neoarch.backend.services.settings import DEFAULT_SETTINGS
from neoarch.frontend.components.console_panel import ConsolePanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_console_wraps_long_lines_by_default(qapp):
    panel = ConsolePanel()

    assert DEFAULT_SETTINGS["console_wrap"] is True
    assert panel.wrap is True
    assert panel.console.lineWrapMode() == QTextEdit.LineWrapMode.WidgetWidth
    assert "Disable line wrap" in panel.wrap_btn.toolTip()


def test_wrap_toggle_updates_mode_and_emits_once(qapp):
    panel = ConsolePanel()
    changes = []
    panel.wrapChanged.connect(changes.append)

    panel.set_wrap(False)
    assert panel.wrap is False
    assert panel.console.lineWrapMode() == QTextEdit.LineWrapMode.NoWrap
    assert "Wrap long lines" in panel.wrap_btn.toolTip()
    assert changes == [False]

    panel.set_wrap(False)
    assert changes == [False]

    panel.set_wrap(True)
    assert changes == [False, True]
