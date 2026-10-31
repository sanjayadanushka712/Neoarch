import json
import subprocess

from neoarch.backend.services import preflight


def _fake_run(sp_out, sp_rc=0, si_out="", si_rc=0):
    def run(cmd, timeout=60):
        if "-Sp" in cmd:
            return subprocess.CompletedProcess(cmd, sp_rc, sp_out, "")
        return subprocess.CompletedProcess(cmd, si_rc, si_out, "")
    return run


SI = (
    "Name            : htop\n"
    "Version         : 3.5.3-1\n"
    "Installed Size  : 9820.16 KiB\n"
    "\n"
    "Name            : ncurses\n"
    "Version         : 6.5-1\n"
    "Installed Size  : 2.00 MiB\n"
)


def test_install_plan_parses_packages_and_totals(monkeypatch):
    monkeypatch.setattr(preflight, "_run", _fake_run(
        "htop|3.5.3-1|extra|184319\nncurses|6.5-1|core|204800\n", si_out=SI))
    plan = preflight.install_plan(["htop"])
    assert plan["ok"] is True
    assert [p["name"] for p in plan["packages"]] == ["htop", "ncurses"]
    assert plan["packages"][0]["repo"] == "extra"
    assert plan["packages"][0]["download_size"] == 184319
    assert plan["packages"][0]["installed_size"] == int(9820.16 * 1024)
    assert plan["total_download"] == 184319 + 204800
    assert plan["total_installed"] == int(9820.16 * 1024) + 2 * 1024 ** 2


def test_install_plan_deduplicates(monkeypatch):
    monkeypatch.setattr(preflight, "_run", _fake_run(
        "htop|3.5.3-1|extra|100\nhtop|3.5.3-1|extra|100\n"))
    plan = preflight.install_plan(["htop"])
    assert len(plan["packages"]) == 1


def test_install_plan_falls_back(monkeypatch):
    monkeypatch.setattr(preflight, "_run", _fake_run("", sp_rc=1))
    assert preflight.install_plan(["nope"])["ok"] is False
    assert preflight.install_plan([])["ok"] is False
    assert preflight.install_plan(["htop"], source="AUR")["ok"] is False


def test_aur_plan_lists_requested_and_missing_deps(monkeypatch):
    monkeypatch.setattr(preflight, "_aur_info", lambda names: [
        {"Name": "yay-bin", "Version": "12.4.1-1",
         "Depends": ["pacman>6.1", "git"], "MakeDepends": ["go"]}])
    monkeypatch.setattr(preflight, "_installed_names",
                        lambda: {"git", "pacman"})

    plan = preflight.install_plan(["yay-bin"], source="AUR")
    assert plan["ok"] is True
    assert [p["name"] for p in plan["packages"]] == ["yay-bin", "go"]
    assert plan["packages"][0]["repo"] == "aur"
    assert plan["packages"][0]["version"] == "12.4.1-1"
    assert plan["packages"][1]["repo"] == ""


def test_aur_plan_falls_back_when_rpc_fails(monkeypatch):
    monkeypatch.setattr(preflight, "_aur_info", lambda names: [])
    assert preflight.install_plan(["x"], source="AUR")["ok"] is False


def test_npm_plan_uses_dry_run(monkeypatch):
    out = json.dumps({"add": [
        {"name": "is-number", "version": "7.0.0"},
        {"name": "kind-of", "version": "6.0.3"},
    ], "added": 2})

    def run(cmd, timeout=60):
        assert cmd[:4] == ["npm", "install", "-g", "--dry-run"]
        return subprocess.CompletedProcess(cmd, 0, out, "")

    monkeypatch.setattr(preflight, "_run", run)
    plan = preflight.install_plan(["is-number"], source="npm")
    assert plan["ok"] is True
    assert [p["name"] for p in plan["packages"]] == ["is-number", "kind-of"]
    assert plan["packages"][0]["repo"] == "npm"


def test_npm_plan_falls_back_on_error(monkeypatch):
    monkeypatch.setattr(
        preflight, "_run",
        lambda cmd, timeout=60: subprocess.CompletedProcess(cmd, 1, "", "boom"))
    assert preflight.install_plan(["x"], source="npm")["ok"] is False


def test_flatpak_plan_includes_runtime(monkeypatch):
    info = {
        "org.gnome.Calculator":
            "Version: 51.1\nDownload Size: 2.0 MB\nInstalled Size: 5.1 MB\n"
            "Runtime: org.gnome.Platform/x86_64/51\n",
        "org.gnome.Platform/x86_64/51":
            "Branch: 51\nDownload Size: 401.7 MB\nInstalled Size: 1.0 GB\n",
    }

    def run(cmd, timeout=60):
        if "remote-info" in cmd:
            return subprocess.CompletedProcess(cmd, 0, info.get(cmd[-1], ""), "")
        if "list" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 1, "", "")

    monkeypatch.setattr(preflight, "_run", run)
    plan = preflight.install_plan(["org.gnome.Calculator"], source="Flatpak")
    assert plan["ok"] is True
    assert [p["name"] for p in plan["packages"]] == [
        "org.gnome.Calculator", "org.gnome.Platform/x86_64/51"]
    assert plan["packages"][0]["version"] == "51.1"
    assert plan["packages"][0]["download_size"] == int(2.0 * 1024 ** 2)
    assert plan["packages"][1]["installed_size"] == 1024 ** 3
    assert plan["total_download"] == int(2.0 * 1024 ** 2) + int(401.7 * 1024 ** 2)


def test_flatpak_plan_skips_installed_runtime(monkeypatch):
    def run(cmd, timeout=60):
        if "remote-info" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0,
                "Version: 1\nDownload Size: 1.0 MB\nInstalled Size: 2.0 MB\n"
                "Runtime: org.gnome.Platform/x86_64/51\n", "")
        if "list" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, "runtime/org.gnome.Platform/x86_64/51\n", "")
        return subprocess.CompletedProcess(cmd, 1, "", "")

    monkeypatch.setattr(preflight, "_run", run)
    plan = preflight.install_plan(["app"], source="Flatpak")
    assert [p["name"] for p in plan["packages"]] == ["app"]
