"""Tests for supported distribution capability profiles."""

from neoarch.backend.services import distro


def test_arch_profile_is_default():
    profile = distro.profile_for({"ID": "arch"})
    assert profile.id == "arch"
    assert profile.name == "Arch Linux"
    assert profile.mirror_tools == ("reflector",)
    assert profile.protects("core")
    assert not profile.protects("endeavouros")


def test_endeavouros_profile_protects_its_repo():
    profile = distro.profile_for({"ID": "endeavouros", "ID_LIKE": "arch"})
    assert profile.id == "endeavouros"
    assert profile.protects("endeavouros")
    assert profile.protects("core")
    assert "endeavouros" in profile.keyrings


def test_cachyos_profile_uses_rate_mirrors_and_protects_prefix():
    profile = distro.profile_for({"ID": "cachyos", "ID_LIKE": "arch"})
    assert profile.id == "cachyos"
    assert profile.mirror_tools[0] == "cachyos-rate-mirrors"
    assert profile.protects("cachyos")
    assert profile.protects("cachyos-extra-v3")
    assert not profile.protects("some-third-party")


def test_garuda_profile_protects_chaotic_aur():
    profile = distro.profile_for({"ID": "garuda", "ID_LIKE": "arch"})
    assert profile.id == "garuda"
    assert profile.protects("garuda")
    assert profile.protects("chaotic-aur")
    assert "garuda" in profile.keyrings
    assert "chaotic" in profile.keyrings


def test_manjaro_profile_uses_pacman_mirrors_and_branch(tmp_path):
    conf = tmp_path / "pacman-mirrors.conf"
    conf.write_text("Branch = testing\n", encoding="utf-8")
    profile = distro.profile_for(
        {"ID": "manjaro", "ID_LIKE": "arch"}, branch=distro.manjaro_branch(str(conf)))
    assert profile.id == "manjaro"
    assert profile.mirror_tools == ("pacman-mirrors",)
    assert profile.branch == "testing"
    assert profile.protects("community")


def test_unknown_arch_derivative_gets_safe_arch_profile():
    profile = distro.profile_for(
        {"ID": "somearch", "ID_LIKE": "arch", "PRETTY_NAME": "Some Arch"})
    assert profile.protects("core")
    assert profile.mirror_tools == ("reflector",)
    assert profile.name == "Some Arch"


def test_available_mirror_tool_prefers_installed_cachyos_tool(monkeypatch):
    profile = distro.profile_for({"ID": "cachyos"})
    monkeypatch.setattr(
        distro.shutil, "which",
        lambda name: "/usr/bin/" + name if name in {"reflector", "cachyos-rate-mirrors"} else None)
    assert distro.available_mirror_tool(profile) == "cachyos-rate-mirrors"


def test_available_mirror_tool_falls_back_to_reflector(monkeypatch):
    profile = distro.profile_for({"ID": "cachyos"})
    monkeypatch.setattr(
        distro.shutil, "which",
        lambda name: "/usr/bin/reflector" if name == "reflector" else None)
    assert distro.available_mirror_tool(profile) == "reflector"


def test_available_keyrings_filters_to_installed(monkeypatch):
    profile = distro.profile_for({"ID": "endeavouros"})
    monkeypatch.setattr(
        distro, "_keyring_exists",
        lambda name: name in {"endeavouros", "archlinux"})
    assert distro.available_keyrings(profile) == ("endeavouros", "archlinux")


def test_available_keyrings_falls_back_to_arch(monkeypatch):
    monkeypatch.setattr(distro, "_keyring_exists", lambda name: False)
    assert distro.available_keyrings(distro.profile_for({"ID": "manjaro"})) == distro.ARCH_KEYRINGS
