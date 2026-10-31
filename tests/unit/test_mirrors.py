"""Tests for the reflector mirror-refresh service."""

import subprocess

import neoarch.backend.services.mirrors as mirrors


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_refresh_without_reflector(monkeypatch):
    monkeypatch.setattr(mirrors, "reflector_path", lambda: None)
    ok, detail = mirrors.refresh_mirrors()
    assert ok is False
    assert "reflector" in detail


def test_refresh_runs_expected_command(monkeypatch, tmp_path):
    mirrorlist = tmp_path / "mirrorlist"
    calls = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        mirrorlist.write_text("Server = https://a/$repo/os/$arch\n"
                              "Server = https://b/$repo/os/$arch\n")
        return _completed()

    monkeypatch.setattr(
        mirrors, "reflector_path", lambda: "/usr/bin/reflector")
    monkeypatch.setattr(mirrors, "MIRRORLIST", str(mirrorlist))
    monkeypatch.setattr(mirrors, "get_auth_command", lambda: ["sudo", "-A"])
    monkeypatch.setattr(
        mirrors, "get_askpass_env", lambda: {"SUDO_ASKPASS": "x"})
    monkeypatch.setattr(mirrors.subprocess, "run", fake_run)

    ok, detail = mirrors.refresh_mirrors(latest=5, country="Germany")
    assert ok is True
    assert detail == "2"
    cmd = calls["cmd"]
    assert cmd[:3] == ["sudo", "-A", "/usr/bin/reflector"]
    assert "--latest" in cmd and cmd[cmd.index("--latest") + 1] == "5"
    assert cmd[cmd.index("--protocol") + 1] == "https"
    assert cmd[cmd.index("--sort") + 1] == "rate"
    assert cmd[cmd.index("--save") + 1] == str(mirrorlist)
    assert cmd[cmd.index("--country") + 1] == "Germany"


def test_refresh_surfaces_error(monkeypatch):
    monkeypatch.setattr(
        mirrors, "reflector_path", lambda: "/usr/bin/reflector")
    monkeypatch.setattr(mirrors.subprocess, "run",
                        lambda cmd, **kw: _completed(1, stderr="boom"))
    ok, detail = mirrors.refresh_mirrors()
    assert ok is False
    assert detail == "boom"


def test_refresh_rejects_empty_mirrorlist(monkeypatch, tmp_path):
    mirrorlist = tmp_path / "mirrorlist"
    mirrorlist.write_text("# empty\n")
    monkeypatch.setattr(
        mirrors, "reflector_path", lambda: "/usr/bin/reflector")
    monkeypatch.setattr(mirrors, "MIRRORLIST", str(mirrorlist))
    monkeypatch.setattr(
        mirrors.subprocess, "run", lambda cmd, **kw: _completed())
    ok, detail = mirrors.refresh_mirrors()
    assert ok is False
    assert "mirror list" in detail


def test_mirrorlist_server_count(monkeypatch, tmp_path):
    mirrorlist = tmp_path / "mirrorlist"
    mirrorlist.write_text("# comment\nServer = a\n\nServer = b\n")
    monkeypatch.setattr(mirrors, "MIRRORLIST", str(mirrorlist))
    assert mirrors.mirrorlist_server_count() == 2


def test_mirrorlist_server_count_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(mirrors, "MIRRORLIST", str(tmp_path / "nope"))
    assert mirrors.mirrorlist_server_count() == 0


def test_refresh_clamps_bad_latest(monkeypatch, tmp_path):
    mirrorlist = tmp_path / "mirrorlist"
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        mirrorlist.write_text("Server = a\n")
        return _completed()

    monkeypatch.setattr(
        mirrors, "reflector_path", lambda: "/usr/bin/reflector")
    monkeypatch.setattr(mirrors, "MIRRORLIST", str(mirrorlist))
    monkeypatch.setattr(mirrors.subprocess, "run", fake_run)
    ok, _ = mirrors.refresh_mirrors(latest="oops")
    assert ok is True
    assert seen["cmd"][seen["cmd"].index("--latest") + 1] == "10"
