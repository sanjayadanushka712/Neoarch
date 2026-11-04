"""Rank pacman mirrors with the tool appropriate for the running distro.

Arch Linux, EndeavourOS, and Garuda use ``reflector``.  Manjaro uses
``pacman-mirrors`` (reflector writes the wrong mirror list there), and
CachyOS prefers ``cachyos-rate-mirrors`` with reflector as a fallback.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional, Tuple

from neoarch.backend.auth import get_auth_command, get_askpass_env
from neoarch.backend.services.distro import (
    DistroProfile, current_profile,
)

MIRRORLIST = "/etc/pacman.d/mirrorlist"
CACHYOS_MIRRORLIST = "/etc/pacman.d/cachyos-mirrorlist"

_NO_TOOL = (
    "No supported mirror tool found. Install reflector, pacman-mirrors, "
    "or cachyos-rate-mirrors for your distribution."
)


def reflector_path():
    """Absolute path to reflector, or None when it is not installed."""
    return shutil.which("reflector")


def available_mirror_tool(profile: Optional[DistroProfile] = None) -> Optional[str]:
    """Return the best installed mirror tool for this distribution."""
    profile = profile or current_profile()
    for tool in profile.mirror_tools:
        if tool == "reflector":
            if reflector_path():
                return tool
        elif shutil.which(tool):
            return tool
    return None


def _server_count(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for line in handle
                       if line.strip().startswith("Server ="))
    except OSError:
        return 0


def mirrorlist_server_count(path: Optional[str] = None) -> int:
    """Number of enabled ``Server =`` entries in the relevant mirror list."""
    if path is not None:
        return _server_count(path)
    count = _server_count(MIRRORLIST)
    if current_profile().id == "cachyos":
        count += _server_count(CACHYOS_MIRRORLIST)
    return count


def _command(tool: str, binary: str, latest: int, country: str):
    if tool == "pacman-mirrors":
        cmd = [binary, "--fasttrack", str(latest)]
        if country:
            cmd.extend(["--country", country])
        return cmd
    if tool == "cachyos-rate-mirrors":
        return [binary]
    cmd = [binary, "--latest", str(latest), "--protocol", "https",
           "--sort", "rate", "--save", MIRRORLIST]
    if country:
        cmd.extend(["--country", country])
    return cmd


def refresh_mirrors(latest: int = 10, country: str = "",
                    timeout: int = 300) -> Tuple[bool, str]:
    """Refresh the distro mirror list.

    Returns ``(ok, detail)``; on success ``detail`` is the number of servers
    written, otherwise it is the error text to show the user.
    """
    tool = available_mirror_tool()
    if not tool:
        return False, _NO_TOOL
    binary = reflector_path() if tool == "reflector" else shutil.which(tool)
    if not binary:
        return False, _NO_TOOL

    try:
        latest = max(1, int(latest))
    except (TypeError, ValueError):
        latest = 10

    cmd = _command(tool, binary, latest, country)
    auth = get_auth_command()
    env = get_askpass_env() if auth == ["sudo", "-A"] else None
    try:
        result = subprocess.run(auth + cmd, capture_output=True, text=True,
                                timeout=timeout, env=env, check=False)
    except subprocess.TimeoutExpired:
        return False, "timed out while contacting mirrors"
    except Exception as exc:
        return False, str(exc)

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return False, detail or "{} exited with an error".format(tool)

    count = mirrorlist_server_count()
    if count <= 0:
        return False, "{} did not write a usable mirror list".format(tool)
    return True, str(count)


__all__ = [
    "CACHYOS_MIRRORLIST", "MIRRORLIST",
    "available_mirror_tool", "mirrorlist_server_count",
    "reflector_path", "refresh_mirrors",
]
