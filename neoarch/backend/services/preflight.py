"""Install preflight: what a source would fetch before it runs."""

from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from typing import Dict, List

from neoarch.backend.services.hygiene import (
    _parse_pacman_fields, _parse_size_text,
)
from neoarch.backend.sys_utils import c_locale_env

AUR_RPC = "https://aur.archlinux.org/rpc/v5/info"
FLATHUB = "flathub"


def _run(cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, check=False, env=c_locale_env())
    except Exception:
        return subprocess.CompletedProcess(cmd, 1, "", "")


def _empty() -> Dict:
    return {"ok": False, "packages": [], "total_download": 0,
            "total_installed": 0}


def _plan(entries: List[Dict]) -> Dict:
    return {
        "ok": True,
        "packages": entries,
        "total_download": sum(e.get("download_size", 0) for e in entries),
        "total_installed": sum(e.get("installed_size", 0) for e in entries),
    }


def install_plan(packages: List[str], source: str = "pacman") -> Dict:
    """Resolve what installing ``packages`` from ``source`` would fetch.

    Returns ``{"ok", "packages", "total_download", "total_installed"}``
    where each package carries ``name``, ``version``, ``repo``,
    ``download_size`` and ``installed_size`` in bytes. ``ok`` is False when
    the source cannot be resolved, so the caller falls back to a plain
    install. AUR rows list direct dependencies only; Flatpak rows cover the
    app and its runtime; npm rows come from a dry-run of the global install.
    """
    names = [p for p in (packages or []) if p]
    if not names:
        return _empty()
    if source == "pacman":
        return _pacman_plan(names)
    if source == "AUR":
        return _aur_plan(names)
    if source == "npm":
        return _npm_plan(names)
    if source == "Flatpak":
        return _flatpak_plan(names)
    return _empty()


# ── pacman ────────────────────────────────────────────────────────────────

def _pacman_plan(names: List[str]) -> Dict:
    result = _run(["pacman", "-Sp", "--print-format", "%n|%v|%r|%s",
                   "--noconfirm"] + names)
    if result.returncode != 0:
        return _empty()

    entries: List[Dict] = []
    seen = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) != 4:
            continue
        name, version, repo, size = parts
        if not name or name in seen:
            continue
        seen.add(name)
        entries.append({
            "name": name,
            "version": version,
            "repo": repo,
            "download_size": int(size) if size.isdigit() else 0,
            "installed_size": 0,
        })
    if not entries:
        return _empty()

    info = _run(["pacman", "-Si"] + [e["name"] for e in entries])
    if info.returncode == 0:
        sizes = {}
        for block in re.split(r"\n\s*\n", info.stdout):
            fields = _parse_pacman_fields(block)
            name = fields.get("Name")
            if name:
                sizes[name] = _parse_size_text(fields.get("Installed Size", ""))
        for entry in entries:
            entry["installed_size"] = sizes.get(entry["name"], 0)
    return _plan(entries)


# ── AUR ───────────────────────────────────────────────────────────────────

def _aur_info(names: List[str]) -> List[Dict]:
    query = urllib.parse.urlencode([("arg[]", n) for n in names])
    try:
        with urllib.request.urlopen(f"{AUR_RPC}?{query}", timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return []
    return [r for r in data.get("results") or [] if r.get("Name")]


def _installed_names() -> set:
    result = _run(["pacman", "-Qq"], timeout=30)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _aur_plan(names: List[str]) -> Dict:
    infos = _aur_info(names)
    if not infos:
        return _empty()

    entries: List[Dict] = []
    known = set()
    for info in infos:
        name = info.get("Name", "")
        if not name or name in known:
            continue
        known.add(name)
        entries.append({
            "name": name,
            "version": info.get("Version", ""),
            "repo": "aur",
            "download_size": 0,
            "installed_size": 0,
        })

    installed = _installed_names()
    for info in infos:
        for dep in (info.get("Depends") or []) + (info.get("MakeDepends") or []):
            base = re.split(r"[<>=]", dep, maxsplit=1)[0].strip()
            if not base or base in installed or base in known:
                continue
            known.add(base)
            entries.append({
                "name": base,
                "version": "",
                "repo": "",
                "download_size": 0,
                "installed_size": 0,
            })
    return _plan(entries)


# ── npm ───────────────────────────────────────────────────────────────────

def _npm_plan(names: List[str]) -> Dict:
    result = _run(["npm", "install", "-g", "--dry-run", "--json"] + names,
                  timeout=120)
    if result.returncode != 0:
        return _empty()
    try:
        data = json.loads(result.stdout or "{}")
    except ValueError:
        return _empty()

    blocks = data if isinstance(data, list) else [data]
    entries: List[Dict] = []
    seen = set()
    for block in blocks:
        for item in block.get("add") or []:
            name = item.get("name", "")
            if not name or name in seen:
                continue
            seen.add(name)
            entries.append({
                "name": name,
                "version": item.get("version", ""),
                "repo": "npm",
                "download_size": 0,
                "installed_size": 0,
            })
    return _plan(entries) if entries else _empty()


# ── Flatpak ───────────────────────────────────────────────────────────────

def _flatpak_info(app_id: str) -> Dict[str, str]:
    for scope in ("--user", "--system"):
        result = _run(["flatpak", scope, "remote-info", FLATHUB, app_id],
                      timeout=60)
        if result.returncode == 0 and result.stdout.strip():
            fields: Dict[str, str] = {}
            for line in result.stdout.splitlines():
                key, sep, value = line.partition(":")
                if sep and key.strip():
                    fields[key.strip()] = value.strip()
            return fields
    return {}


def _flatpak_installed(ref: str) -> bool:
    result = _run(["flatpak", "list", "--columns=ref"], timeout=30)
    if result.returncode != 0:
        return False
    return ref in result.stdout


def _flatpak_plan(names: List[str]) -> Dict:
    entries: List[Dict] = []
    for app_id in names:
        fields = _flatpak_info(app_id)
        if not fields:
            continue
        entries.append({
            "name": app_id,
            "version": fields.get("Version", ""),
            "repo": FLATHUB,
            "download_size": _parse_size_text(fields.get("Download Size", "")),
            "installed_size": _parse_size_text(fields.get("Installed Size", "")),
        })
        runtime = fields.get("Runtime", "")
        if runtime and not _flatpak_installed(runtime):
            runtime_fields = _flatpak_info(runtime)
            if runtime_fields:
                entries.append({
                    "name": runtime,
                    "version": runtime_fields.get("Branch", ""),
                    "repo": FLATHUB,
                    "download_size": _parse_size_text(
                        runtime_fields.get("Download Size", "")),
                    "installed_size": _parse_size_text(
                        runtime_fields.get("Installed Size", "")),
                })
    return _plan(entries) if entries else _empty()
