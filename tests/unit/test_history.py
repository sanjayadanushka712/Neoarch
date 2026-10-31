"""Tests for pacman history parsing and the History page."""

import pytest

from neoarch.backend.services import history


SAMPLE = (
    "[2026-10-20T10:00:00+0200] [ALPM] transaction started\n"
    "[2026-10-20T10:00:01+0200] [ALPM] upgraded bash (5.2.037-1 -> 5.3.0-1)\n"
    "[2026-10-20T10:00:01+0200] [ALPM] installed htop (3.4.1-1)\n"
    "[2026-10-20T10:00:02+0200] [ALPM] transaction completed\n"
    "[2026-10-21T09:00:00+0200] [ALPM] transaction started\n"
    "[2026-10-21T09:00:01+0200] [ALPM] removed htop (3.4.1-1)\n"
    "[2026-10-21T09:00:02+0200] [ALPM] transaction completed\n"
)


def _log(tmp_path, text):
    path = tmp_path / "pacman.log"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_read_history_groups_transactions(tmp_path):
    transactions = history.read_history(_log(tmp_path, SAMPLE))
    assert len(transactions) == 2
    newest, older = transactions
    assert [p["name"] for p in newest["packages"]] == ["htop"]
    assert newest["packages"][0]["action"] == "remove"
    assert [p["action"] for p in older["packages"]] == ["upgrade", "install"]
    assert [p["name"] for p in older["packages"]] == ["bash", "htop"]


def test_upgrade_keeps_old_and_new_versions(tmp_path):
    transactions = history.read_history(_log(tmp_path, SAMPLE))
    upgrade = transactions[1]["packages"][0]
    assert upgrade["old_version"] == "5.2.037-1"
    assert upgrade["version"] == "5.3.0-1"


def test_removed_keeps_the_version(tmp_path):
    transactions = history.read_history(_log(tmp_path, SAMPLE))
    removed = transactions[0]["packages"][0]
    assert removed["version"] == "3.4.1-1"
    assert removed["old_version"] == ""


def test_timestamps_are_parsed(tmp_path):
    transactions = history.read_history(_log(tmp_path, SAMPLE))
    assert transactions[0]["timestamp"].hour == 9
    assert transactions[1]["timestamp"].hour == 10


def test_missing_log_returns_empty(tmp_path):
    assert history.read_history(str(tmp_path / "nope.log")) == []


def test_unrelated_lines_are_ignored(tmp_path):
    text = (
        "[2026-10-20T10:00:00+0200] [PACMAN] Running 'pacman -S htop'\n"
        "[2026-10-20T10:00:00+0200] [ALPM] warning: /etc/pacman.conf\n"
        "garbage without a timestamp\n"
        "[2026-10-20T10:00:01+0200] [ALPM] installed htop (3.4.1-1)\n"
    )
    transactions = history.read_history(_log(tmp_path, text))
    assert len(transactions) == 1
    assert transactions[0]["packages"] == [
        {"action": "install", "name": "htop", "version": "3.4.1-1",
         "old_version": ""}
    ]


def test_event_without_transaction_marker_starts_one(tmp_path):
    text = (
        "[2026-10-20T10:00:01+0200] [ALPM] installed htop (3.4.1-1)\n"
        "[2026-10-20T10:00:02+0200] [ALPM] reinstalled bash (5.3.0-1)\n"
    )
    transactions = history.read_history(_log(tmp_path, text))
    assert len(transactions) == 1
    assert len(transactions[0]["packages"]) == 2


def test_read_history_reads_only_the_tail(tmp_path):
    path = _log(tmp_path, SAMPLE * 100)
    transactions = history.read_history(path, limit=10, max_bytes=200)
    assert transactions
    assert transactions[0]["packages"][0]["action"] == "remove"
    assert transactions[0]["packages"][0]["name"] == "htop"


def test_limit_keeps_the_newest(tmp_path):
    transactions = history.read_history(_log(tmp_path, SAMPLE), limit=1)
    assert len(transactions) == 1
    assert transactions[0]["packages"][0]["action"] == "remove"


def test_history_stats_counts_actions(tmp_path):
    stats = history.history_stats(history.read_history(_log(tmp_path, SAMPLE)))
    assert stats["transactions"] == 2
    assert stats["install"] == 1
    assert stats["upgrade"] == 1
    assert stats["remove"] == 1


def test_downgrade_and_reinstall_actions(tmp_path):
    text = (
        "[2026-10-20T10:00:01+0200] [ALPM] downgraded bash (5.3.0-1 -> 5.2.037-1)\n"
        "[2026-10-20T10:00:02+0200] [ALPM] reinstalled htop (3.4.1-1)\n"
    )
    packages = history.read_history(_log(tmp_path, text))[0]["packages"]
    assert packages[0]["action"] == "downgrade"
    assert packages[0]["old_version"] == "5.3.0-1"
    assert packages[0]["version"] == "5.2.037-1"
    assert packages[1]["action"] == "reinstall"


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_history_tab_renders_and_filters(qapp, monkeypatch, tmp_path):
    from neoarch.frontend.components import history_tab as tab_module

    transactions = history.read_history(_log(tmp_path, SAMPLE))
    monkeypatch.setattr(tab_module, "read_history", lambda: transactions)
    tab = tab_module.HistoryTab()
    tab._apply(transactions)
    tab.show()

    assert tab._stat_values["transactions"].text() == "2"
    assert tab._stat_values["install"].text() == "1"
    assert tab._stat_values["remove"].text() == "1"

    tab.set_search_text("bash")
    visible = tab._visible_transactions()
    assert len(visible) == 1
    assert [p["name"] for p in visible[0]["packages"]] == ["bash"]

    tab.set_search_text("no-such-package")
    assert tab._visible_transactions() == []


def test_history_tab_empty_state(qapp, monkeypatch):
    from neoarch.frontend.components import history_tab as tab_module

    monkeypatch.setattr(tab_module, "read_history", lambda: [])
    tab = tab_module.HistoryTab()
    tab._apply([])
    tab.show()
    assert tab._stat_values["transactions"].text() == "0"
    assert tab._empty_label.isVisible() is True
    assert "No history" in tab._empty_label.text()


def test_history_tab_filters_by_action(qapp, monkeypatch, tmp_path):
    from neoarch.frontend.components import history_tab as tab_module

    transactions = history.read_history(_log(tmp_path, SAMPLE))
    monkeypatch.setattr(tab_module, "read_history", lambda: transactions)
    tab = tab_module.HistoryTab()
    tab._apply(transactions)

    tab._set_action_filter("install")
    visible = tab._visible_transactions()
    assert [p["name"] for t in visible for p in t["packages"]] == ["htop"]
    assert tab._filter_buttons["install"].isChecked()
    assert not tab._filter_buttons[None].isChecked()

    tab._set_action_filter(None)
    assert len(tab._visible_transactions()) == 2
    assert tab._filter_buttons[None].isChecked()
