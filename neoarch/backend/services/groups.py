"""Browse pacman package groups from the synced databases.

Groups are read straight from the ``*.db`` archives under
``/var/lib/pacman/sync`` so no network access is needed and no per-group
``pacman -Sg`` calls are spawned. Installed state comes from ``pacman -Qq``.
"""

from __future__ import annotations

import glob
import os
import subprocess
import tarfile
from typing import Dict, List

from neoarch.backend.services.preflight import _parse_desc

SYNC_DIR = "/var/lib/pacman/sync"

_groups_cache: Dict[str, List[Dict]] | None = None


def _run(cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except Exception:
        return subprocess.CompletedProcess(cmd, 1, "", "")


def _installed_names() -> set:
    result = _run(["pacman", "-Qq"])
    if result.returncode != 0:
        return set()
    return set(result.stdout.split())


def load_groups(refresh: bool = False) -> Dict[str, List[Dict]]:
    """Map group name to its repo packages (cached per session).

    Each entry is ``{"name", "version", "repo", "installed"}``.
    """
    global _groups_cache
    if _groups_cache is not None and not refresh:
        return _groups_cache

    installed = _installed_names()
    mapping: Dict[str, List[Dict]] = {}
    for db in sorted(glob.glob(os.path.join(SYNC_DIR, "*.db"))):
        repo = os.path.basename(db)[:-3]
        try:
            with tarfile.open(db, "r:*") as tar:
                for member in tar:
                    if not member.name.endswith("/desc"):
                        continue
                    handle = tar.extractfile(member)
                    if handle is None:
                        continue
                    fields = _parse_desc(
                        handle.read().decode("utf-8", errors="replace"))
                    names = fields.get("NAME") or []
                    if not names:
                        continue
                    pkg = names[0]
                    version = (fields.get("VERSION") or [""])[0]
                    for group in fields.get("GROUPS") or []:
                        mapping.setdefault(group, []).append({
                            "name": pkg,
                            "version": version,
                            "repo": repo,
                            "installed": pkg in installed,
                        })
        except Exception:
            continue

    for entries in mapping.values():
        entries.sort(key=lambda entry: entry["name"].lower())
    _groups_cache = mapping
    return mapping


def list_groups(refresh: bool = False) -> List[Dict]:
    """Every group with its package and installed counts, sorted by name."""
    mapping = load_groups(refresh=refresh)
    groups = [
        {
            "name": name,
            "count": len(entries),
            "installed": sum(1 for entry in entries if entry["installed"]),
        }
        for name, entries in mapping.items()
    ]
    groups.sort(key=lambda group: group["name"].lower())
    return groups


def group_packages(group: str, refresh: bool = False) -> List[Dict]:
    """Packages that belong to ``group`` (empty when unknown)."""
    return list(load_groups(refresh=refresh).get(group, []))


def clear_cache():
    """Drop the cached group map (used by tests and manual refreshes)."""
    global _groups_cache
    _groups_cache = None
