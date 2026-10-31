import subprocess

from neoarch.backend.services import hygiene


def test_package_files_drops_directories_and_caches(monkeypatch):
    calls = []

    def fake_run(cmd, timeout=60, env=None):
        calls.append(cmd)
        return subprocess.CompletedProcess(
            cmd, 0,
            "/usr/bin/bash\n/usr/share/doc/bash/\n/usr/share/doc/bash/README\n",
            "")

    monkeypatch.setattr(hygiene, "_run", fake_run)
    monkeypatch.setattr(hygiene, "_FILES_CACHE", {})

    assert hygiene.package_files("bash") == [
        "/usr/bin/bash", "/usr/share/doc/bash/README"]
    assert hygiene.package_files("bash") == [
        "/usr/bin/bash", "/usr/share/doc/bash/README"]
    assert len(calls) == 1
    assert calls[0] == ["pacman", "-Qlq", "bash"]


def test_package_files_empty_on_failure(monkeypatch):
    monkeypatch.setattr(
        hygiene, "_run",
        lambda cmd, timeout=60, env=None: subprocess.CompletedProcess(cmd, 1, "", "error"))
    monkeypatch.setattr(hygiene, "_FILES_CACHE", {})

    assert hygiene.package_files("missing") == []
    assert hygiene.package_files("") == []
