"""Tests for the pacman package-group service."""

import io
import subprocess
import tarfile

import pytest

import neoarch.backend.services.groups as groups


@pytest.fixture(autouse=True)
def _clear_cache():
    groups.clear_cache()
    yield
    groups.clear_cache()


def _make_db(path, entries):
    with tarfile.open(path, "w:gz") as tar:
        for name, version, group_names in entries:
            body = (
                f"%NAME%\n{name}\n\n%VERSION%\n{version}\n\n"
                f"%GROUPS%\n" + "\n".join(group_names) + "\n")
            raw = body.encode()
            info = tarfile.TarInfo(f"{name}-{version}/desc")
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))


def _installed(monkeypatch, names):
    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["pacman", "-Qq"]:
            return subprocess.CompletedProcess(cmd, 0, "\n".join(names), "")
        return subprocess.CompletedProcess(cmd, 1, "", "")

    monkeypatch.setattr(groups, "_run", fake_run)


def test_load_groups_and_installed(monkeypatch, tmp_path):
    _make_db(tmp_path / "core.db", [
        ("bash", "5.2-1", ["base", "shells"]),
        ("zsh", "5.9-1", ["shells"]),
    ])
    _make_db(tmp_path / "extra.db", [
        ("vim", "9.1-1", ["editors"]),
    ])
    monkeypatch.setattr(groups, "SYNC_DIR", str(tmp_path))
    _installed(monkeypatch, ["bash"])

    mapping = groups.load_groups()
    assert set(mapping) == {"base", "shells", "editors"}
    assert [e["name"] for e in mapping["shells"]] == ["bash", "zsh"]
    assert mapping["shells"][0] == {
        "name": "bash", "version": "5.2-1", "repo": "core",
        "installed": True}
    assert mapping["shells"][1]["installed"] is False
    assert mapping["editors"][0]["repo"] == "extra"


def test_list_groups_counts(monkeypatch, tmp_path):
    _make_db(tmp_path / "core.db", [
        ("bash", "5.2-1", ["shells"]),
        ("zsh", "5.9-1", ["shells"]),
    ])
    monkeypatch.setattr(groups, "SYNC_DIR", str(tmp_path))
    _installed(monkeypatch, ["zsh"])

    listing = groups.list_groups()
    assert [g["name"] for g in listing] == ["shells"]
    assert listing[0]["count"] == 2
    assert listing[0]["installed"] == 1


def test_group_packages_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(groups, "SYNC_DIR", str(tmp_path))
    _installed(monkeypatch, [])
    assert groups.group_packages("missing") == []


def test_cache_reused_until_refresh(monkeypatch, tmp_path):
    _make_db(tmp_path / "core.db", [("bash", "5.2-1", ["shells"])])
    monkeypatch.setattr(groups, "SYNC_DIR", str(tmp_path))
    _installed(monkeypatch, [])

    opens = {"n": 0}
    real_open = tarfile.open

    def counting_open(*args, **kwargs):
        opens["n"] += 1
        return real_open(*args, **kwargs)

    monkeypatch.setattr(groups.tarfile, "open", counting_open)
    groups.load_groups()
    groups.load_groups()
    assert opens["n"] == 1
    groups.load_groups(refresh=True)
    assert opens["n"] == 2


def test_bad_archive_is_skipped(monkeypatch, tmp_path):
    (tmp_path / "broken.db").write_text("not a tarball")
    _make_db(tmp_path / "core.db", [("bash", "5.2-1", ["shells"])])
    monkeypatch.setattr(groups, "SYNC_DIR", str(tmp_path))
    _installed(monkeypatch, [])

    mapping = groups.load_groups()
    assert set(mapping) == {"shells"}


def test_missing_sync_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(groups, "SYNC_DIR", str(tmp_path / "nope"))
    _installed(monkeypatch, [])
    assert groups.list_groups() == []
