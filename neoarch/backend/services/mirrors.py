"""Rank pacman mirrors with reflector and write a fresh mirror list."""

from __future__ import annotations

import shutil
import subprocess
from typing import Tuple

from neoarch.backend.auth import get_auth_command, get_askpass_env

MIRRORLIST = "/etc/pacman.d/mirrorlist"


def reflector_path():
    """Absolute path to reflector, or None when it is not installed."""
    return shutil.which("reflector")


def mirrorlist_server_count() -> int:
    """Number of enabled ``Server =`` entries in the mirror list."""
    try:
        with open(MIRRORLIST, "r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for line in fh
                       if line.strip().startswith("Server ="))
    except OSError:
        return 0


def refresh_mirrors(latest: int = 10, country: str = "",
                    timeout: int = 300) -> Tuple[bool, str]:
    """Run reflector and save the fastest HTTPS mirrors.

    Returns ``(ok, detail)``; on success ``detail`` is the number of servers
    written, otherwise it is the error text to show the user.
    """
    binary = reflector_path()
    if not binary:
        return False, "reflector is not installed"
    try:
        latest = max(1, int(latest))
    except (TypeError, ValueError):
        latest = 10

    cmd = [binary, "--latest", str(latest), "--protocol", "https",
           "--sort", "rate", "--save", MIRRORLIST]
    if country:
        cmd.extend(["--country", country])

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
        return False, detail or "reflector exited with an error"

    count = mirrorlist_server_count()
    if count <= 0:
        return False, "reflector did not write a usable mirror list"
    return True, str(count)
