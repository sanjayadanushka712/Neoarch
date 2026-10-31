import types

from neoarch.frontend.mixins.operations import _OperationsMixin
from neoarch.frontend.mixins.views import _ViewsMixin


class _Signal:
    def emit(self, *args):
        pass


class _Stub(_ViewsMixin):
    def __init__(self):
        self.logs = []
        self.installed = []

    def log(self, message):
        self.logs.append(message)

    def _install_many_now(self, packages_by_source, optional_by_source=None):
        self.installed.append((packages_by_source, optional_by_source or {}))


def test_confirm_install_plans_merges_sources_and_routes_optionals(monkeypatch):
    stub = _Stub()
    calls = []

    def fake_show(parent, plan):
        calls.append(plan)
        return ["ttf-dejavu", "extra-opt"]

    monkeypatch.setattr(
        "neoarch.frontend.components.install_preflight_dialog.show_install_plan",
        fake_show)

    plans = [
        ("pacman", {
            "ok": True,
            "packages": [
                {"name": "htop", "version": "3", "repo": "extra",
                 "download_size": 100, "installed_size": 200},
            ],
            "optional": [
                {"name": "ttf-dejavu", "description": "font"},
            ],
            "total_download": 100,
            "total_installed": 200,
        }),
        ("AUR", {
            "ok": True,
            "packages": [
                {"name": "yay-bin", "version": "12", "repo": "aur",
                 "download_size": 0, "installed_size": 0},
            ],
            "optional": [
                {"name": "extra-opt", "description": "extra"},
            ],
            "total_download": 0,
            "total_installed": 0,
        }),
    ]

    stub._confirm_install_plans(
        {"pacman": ["htop"], "AUR": ["yay-bin"]}, plans)

    assert [p["name"] for p in calls[0]["packages"]] == ["htop", "yay-bin"]
    assert calls[0]["total_download"] == 100
    assert calls[0]["total_installed"] == 200
    assert stub.installed == [(
        {"pacman": ["htop"], "AUR": ["yay-bin"]},
        {"pacman": ["ttf-dejavu"], "AUR": ["extra-opt"]},
    )]


def test_confirm_install_plans_lists_unresolved_packages(monkeypatch):
    stub = _Stub()
    calls = []

    def fake_show(parent, plan):
        calls.append(plan)
        return []

    monkeypatch.setattr(
        "neoarch.frontend.components.install_preflight_dialog.show_install_plan",
        fake_show)

    stub._confirm_install_plans(
        {"pacman": ["htop"], "AUR": ["missing-pkg"]},
        [("pacman", {"ok": False}), ("AUR", {"ok": False})])

    names = [p["name"] for p in calls[0]["packages"]]
    assert names == ["htop", "missing-pkg"]
    assert calls[0]["total_download"] == 0
    assert stub.installed == [(
        {"pacman": ["htop"], "AUR": ["missing-pkg"]}, {})]


def test_discover_install_selected_uses_preflight(monkeypatch):
    class Stub:
        current_view = "discover"
        installed_index = {}
        updates_table = object()

        def __init__(self):
            self.preflight = []
            self.logs = []

        def get_checked_packages_for_view(self):
            return [
                {"name": "htop", "source": "pacman"},
                {"name": "yay-bin", "source": "AUR"},
                {"name": "installed", "source": "pacman", "_installed": True},
            ]

        def build_installed_index(self, selected=None):
            pass

        def ensure_session_auth(self):
            return True

        def _start_install_preflight_many(self, packages_by_source):
            self.preflight.append(packages_by_source)

        def log_signal(self):
            raise AssertionError("unused")

    stub = Stub()
    stub.log_signal = _Signal()
    stub.install_selected = types.MethodType(
        _OperationsMixin.install_selected, stub)

    stub.install_selected()

    assert stub.preflight == [{"pacman": ["htop"], "AUR": ["yay-bin"]}]
