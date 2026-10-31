from datetime import datetime

import pytest
from PyQt6.QtWidgets import QApplication, QLabel

from neoarch.frontend.components.package_history_dialog import (
    PackageHistoryDialog, _format_date, _history_rows,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


ENTRIES = [
    {"timestamp": datetime(2026, 10, 31, 14, 22),
     "packages": [{"action": "upgrade", "name": "bash", "version": "5.2.037-1",
                   "old_version": "5.2.026-1"}]},
    {"timestamp": datetime(2026, 10, 1, 9, 5),
     "packages": [{"action": "install", "name": "bash", "version": "5.2.026-1",
                   "old_version": ""}]},
]


def test_history_rows_flatten_newest_first():
    rows = _history_rows(ENTRIES)
    assert [e["action"] for _ts, e in rows] == ["upgrade", "install"]
    assert rows[0][0] == datetime(2026, 10, 31, 14, 22)


def test_format_date_handles_missing_timestamp():
    assert _format_date(None) == "—"
    assert _format_date(datetime(2026, 10, 31, 14, 22)) == "Oct 31, 2026 · 14:22"


def test_dialog_lists_transactions(qapp):
    dlg = PackageHistoryDialog(None, "bash", ENTRIES)
    texts = [lbl.text() for lbl in dlg.findChildren(QLabel)]
    assert "bash" in texts
    assert "2 transactions" in texts
    assert "Oct 31, 2026 · 14:22" in texts
    assert "5.2.026-1  →  5.2.037-1" in texts
    assert "Installed" in texts
    assert "Upgraded" in texts


def test_dialog_empty_state(qapp):
    dlg = PackageHistoryDialog(None, "curl", [])
    texts = [lbl.text() for lbl in dlg.findChildren(QLabel)]
    assert "0 transactions" in texts
    assert "No transactions for this package yet." in texts
