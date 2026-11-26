"""Detection and capability profiles for supported Arch-based systems.

NeoArch targets Arch Linux and a small, explicitly tested set of
Arch-based distributions.  Package operations are identical everywhere
(pacman, AUR, Flatpak, npm); the differences are mirror tooling, distro
owned repositories, keyrings, and Manjaro's release branch.

The profile is intentionally small.  Behaviour should be driven by
capabilities (which tool is installed) rather than by guesswork, while
the profile supplies labels, protected repos, and distro keyrings.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, replace
from typing import Dict, Mapping, Optional, Tuple

__all__ = [
    "ARCH_KEYRINGS",
    "BASE_PROTECTED_REPOS",
    "DistroProfile",
    "OS_RELEASE_PATH",
    "PACMAN_MIRRORS_CONF",
    "available_keyrings",
    "available_mirror_tool",
    "current_profile",
    "distro_keyrings",
    "is_protected_repo",
    "manjaro_branch",
    "profile_for",
    "protected_repo_names",
    "read_os_release",
]

OS_RELEASE_PATH = "/etc/os-release"
PACMAN_MIRRORS_CONF = "/etc/pacman-mirrors.conf"
KEYRING_DIR = "/usr/share/pacman/keyrings"

ARCH_KEYRINGS = ("archlinux", "archlinux32", "archlinuxarm")
BASE_PROTECTED_REPOS = frozenset({"core", "extra", "multilib", "testing"})


@dataclass(frozen=True)
class DistroProfile:
    """Capabilities that differ between supported Arch-based systems."""

    id: str
    name: str
    mirror_tools: Tuple[str, ...] = ("reflector",)
    protected_repos: frozenset = BASE_PROTECTED_REPOS
    protected_prefixes: Tuple[str, ...] = ()
    keyrings: Tuple[str, ...] = ARCH_KEYRINGS
    branch: str = ""

    @property
    def is_arch(self) -> bool:
        return self.id in {"arch", "endeavouros", "cachyos", "garuda", "manjaro"}

    def protects(self, name: str) -> bool:
        value = (name or "").strip().lower()
        if not value:
            return False
        if value in self.protected_repos:
            return True
        return any(value.startswith(prefix) for prefix in self.protected_prefixes)


_ARCH = DistroProfile("arch", "Arch Linux")

_PROFILES: Dict[str, DistroProfile] = {
    "arch": _ARCH,
    "endeavouros": DistroProfile(
        "endeavouros",
        "EndeavourOS",
        protected_repos=BASE_PROTECTED_REPOS | {"endeavouros"},
        keyrings=("endeavouros",) + ARCH_KEYRINGS,
    ),
    "cachyos": DistroProfile(
        "cachyos",
        "CachyOS",
        mirror_tools=("cachyos-rate-mirrors", "reflector"),
        protected_prefixes=("cachyos",),
        keyrings=("cachyos",) + ARCH_KEYRINGS,
    ),
    "garuda": DistroProfile(
        "garuda",
        "Garuda Linux",
        protected_repos=BASE_PROTECTED_REPOS | {"garuda", "chaotic-aur"},
        keyrings=("garuda", "chaotic") + ARCH_KEYRINGS,
    ),
    "manjaro": DistroProfile(
        "manjaro",
        "Manjaro",
        mirror_tools=("pacman-mirrors",),
        protected_repos=BASE_PROTECTED_REPOS | {"community"},
        keyrings=("manjaro",) + ARCH_KEYRINGS,
    ),
}


def read_os_release(path: Optional[str] = None) -> Dict[str, str]:
    """Parse a systemd-style ``os-release`` file into ``{KEY: value}``."""
    if path is None:
        path = OS_RELEASE_PATH
    data: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                data[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return data


def manjaro_branch(path: Optional[str] = None) -> str:
    """Return Manjaro's configured branch (stable/testing/unstable)."""
    if path is None:
        path = PACMAN_MIRRORS_CONF
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                low = line.strip().lower()
                if low.startswith("branch") and "=" in low:
                    return low.split("=", 1)[1].strip() or ""
    except OSError:
        pass
    return ""


def _normalise_ids(release: Mapping[str, str]) -> Tuple[str, ...]:
    values = [release.get("ID", ""), release.get("ID_LIKE", "")]
    ids = []
    for value in values:
        for item in str(value or "").replace(",", " ").split():
            item = item.strip().lower()
            if item and item not in ids:
                ids.append(item)
    return tuple(ids)


def profile_for(release: Optional[Mapping[str, str]] = None,
                branch: Optional[str] = None) -> DistroProfile:
    """Return the capability profile for a parsed ``os-release`` mapping."""
    release = release or read_os_release()
    ids = _normalise_ids(release)

    def _known(key):
        profile = _PROFILES[key]
        if key == "manjaro":
            profile = replace(profile, branch=branch if branch is not None
                              else manjaro_branch())
        return profile

    primary = str(release.get("ID", "")).strip().lower()
    if primary in _PROFILES:
        return _known(primary)

    for key in ids:
        if key in _PROFILES and key != "arch":
            return _known(key)

    # Any other Arch-like system gets the conservative Arch profile.
    if "arch" in ids:
        name = (release.get("PRETTY_NAME") or release.get("NAME")
                or "Arch Linux")
        return replace(_ARCH, id=(ids[0] if ids else "arch"), name=name)
    return _ARCH


def current_profile() -> DistroProfile:
    """Return the profile for the running system."""
    return profile_for(read_os_release())


def protected_repo_names(profile: Optional[DistroProfile] = None) -> frozenset:
    """Return repository names that must not be disabled from the UI."""
    profile = profile or current_profile()
    return frozenset(profile.protected_repos)


def is_protected_repo(name: str) -> bool:
    """True when a repository belongs to the distro/Arch base and is protected."""
    return current_profile().protects(name)


def available_mirror_tool(profile: Optional[DistroProfile] = None) -> Optional[str]:
    """Return the first installed mirror tool for the current distro."""
    profile = profile or current_profile()
    for tool in profile.mirror_tools:
        if shutil.which(tool):
            return tool
    return None


def _keyring_exists(name: str) -> bool:
    return os.path.isfile(os.path.join(KEYRING_DIR, name + ".gpg"))


def available_keyrings(profile: Optional[DistroProfile] = None) -> Tuple[str, ...]:
    """Return distro keyrings that are actually installed on this system."""
    profile = profile or current_profile()
    found = tuple(name for name in profile.keyrings if _keyring_exists(name))
    return found or ARCH_KEYRINGS


def distro_keyrings(profile: Optional[DistroProfile] = None) -> Tuple[str, ...]:
    """Alias for the profile's installed keyring names."""
    return available_keyrings(profile)
