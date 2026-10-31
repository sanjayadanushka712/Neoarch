import subprocess

from neoarch.backend.services import preflight


SI_FIREFOX = (
    "Repository      : extra\n"
    "Name            : firefox\n"
    "Version         : 143.0-1\n"
    "Depends On      : alsa-lib bash ttf-font\n"
    "\n"
)


def _fake_run(out=SI_FIREFOX, rc=0):
    def run(cmd, timeout=60):
        return subprocess.CompletedProcess(cmd, rc, out, "")
    return run


TTF_OPTIONS = [
    {"name": "ttf-dejavu", "version": "2.37", "repo": "extra"},
    {"name": "ttf-liberation", "version": "2.1", "repo": "extra"},
]


def test_provider_choices_for_virtual_dependency(monkeypatch):
    monkeypatch.setattr(preflight, "_run", _fake_run())
    monkeypatch.setattr(preflight, "_installed_names", lambda: set())
    monkeypatch.setattr(preflight, "_real_packages", lambda names: set())
    monkeypatch.setattr(preflight, "providers_for",
                        lambda name: TTF_OPTIONS if name == "ttf-font" else [])
    choices = preflight.provider_choices(["firefox"])
    assert choices == [{"requested": "ttf-font", "options": TTF_OPTIONS}]


def test_provider_choices_skip_when_one_provider_remains(monkeypatch):
    monkeypatch.setattr(preflight, "_run", _fake_run())
    monkeypatch.setattr(preflight, "_installed_names",
                        lambda: {"ttf-dejavu"})
    monkeypatch.setattr(preflight, "_real_packages", lambda names: set())
    monkeypatch.setattr(preflight, "providers_for",
                        lambda name: TTF_OPTIONS if name == "ttf-font" else [])
    assert preflight.provider_choices(["firefox"]) == []


def test_provider_choices_skip_real_packages(monkeypatch):
    monkeypatch.setattr(preflight, "_run", _fake_run())
    monkeypatch.setattr(preflight, "_installed_names", lambda: set())
    monkeypatch.setattr(preflight, "_real_packages",
                        lambda names: {"ttf-font"})
    monkeypatch.setattr(preflight, "providers_for",
                        lambda name: TTF_OPTIONS if name == "ttf-font" else [])
    assert preflight.provider_choices(["firefox"]) == []


def test_provider_choices_for_aur_dependencies(monkeypatch):
    monkeypatch.setattr(preflight, "_aur_info", lambda names: [
        {"Name": "some-aur-pkg", "Depends": ["ttf-font"],
         "MakeDepends": []}])
    monkeypatch.setattr(preflight, "_installed_names", lambda: set())
    monkeypatch.setattr(preflight, "_real_packages", lambda names: set())
    monkeypatch.setattr(preflight, "providers_for", lambda name: TTF_OPTIONS)
    choices = preflight.provider_choices(["some-aur-pkg"], source="AUR")
    assert choices == [{"requested": "ttf-font", "options": TTF_OPTIONS}]


def test_provider_choices_without_dependencies(monkeypatch):
    monkeypatch.setattr(preflight, "_run", _fake_run(
        "Name            : htop\nDepends On      : None\n\n"))
    monkeypatch.setattr(preflight, "_installed_names", lambda: set())
    assert preflight.provider_choices(["htop"]) == []


def test_parse_desc_reads_multivalue_fields():
    fields = preflight._parse_desc(
        "%NAME%\nbash\n\n%VERSION%\n5.3\n\n%PROVIDES%\nsh\nbash=5.3\n")
    assert fields["NAME"] == ["bash"]
    assert fields["PROVIDES"] == ["sh", "bash=5.3"]


def test_providers_for_uses_cache(monkeypatch):
    monkeypatch.setattr(preflight, "_providers_cache", {
        "sh": [{"name": "bash", "version": "5.3", "repo": "core"}]})
    assert preflight.providers_for("sh") == [
        {"name": "bash", "version": "5.3", "repo": "core"}]
    assert preflight.providers_for("nope") == []
