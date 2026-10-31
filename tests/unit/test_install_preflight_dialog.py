import pytest
from PyQt6.QtWidgets import QApplication, QLabel

from neoarch.frontend.components.install_preflight_dialog import (
    InstallPreflightDialog, _fmt_size,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


PLAN = {
    "ok": True,
    "packages": [
        {"name": "htop", "version": "3.5.3-1", "repo": "extra",
         "download_size": 184319, "installed_size": 10055680},
        {"name": "ncurses", "version": "6.5-1", "repo": "core",
         "download_size": 204800, "installed_size": 2097152},
    ],
    "total_download": 389119,
    "total_installed": 12152832,
}


def test_dialog_summarises_plan(qapp):
    dlg = InstallPreflightDialog(None, PLAN)
    texts = [lbl.text() for lbl in dlg.findChildren(QLabel)]
    assert "2 packages will be installed" in texts
    assert "Download size" in texts
    assert "Installed size" in texts
    assert "380.0 KiB" in texts
    assert "11.6 MiB" in texts
    assert "htop" in texts
    assert "3.5.3-1" in texts
    assert "extra" in texts


def test_format_size():
    assert _fmt_size(0) == "—"
    assert _fmt_size(512) == "512 B"
    assert _fmt_size(2048) == "2.0 KiB"
