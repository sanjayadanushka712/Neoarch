"""Release-notes service.

Provides the app with a human-curated changelog and a best-effort "latest
release on GitHub" lookup so the UI can:

* show a *What's New* summary after the app has been updated, and
* tell the user when a newer release exists.

The changelog lives in ``CHANGELOG.md`` at the project root and ships with
the package, so installed (non-git) users get descriptive release notes too.

This module is Qt-free (used by the GUI and potentially the CLI).
"""

import os
import re
import json
import time
import urllib.request
from typing import Dict, List, Optional

from neoarch.resources.paths import PROJECT_ROOT, APP_NAME

__all__ = [
    "parse_changelog",
    "whats_new",
    "version_key",
    "latest_release",
    "commit_count",
    "changelog_versions",
    "CHANGELOG_PATH",
    "REPO_STATS_CACHE",
]

CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.md"

_REPO_URL = "https://api.github.com/repos/sanjayadanushka712/Neoarch"
_RELEASE_URL = f"{_REPO_URL}/releases/latest"
_COMMITS_URL = f"{_REPO_URL}/commits?per_page=1"
REPO_STATS_CACHE = os.path.join(
    os.path.expanduser("~"), ".cache", "neoarch", "repo-stats.json")
_STATS_TTL = 24 * 60 * 60

SECTION_LABELS = ("New Features", "Bug Fixes", "Improvements")

_VERSION_TOKEN_RE = re.compile(r"\d+")

_UNRELEASED_KEY = (1 << 30,)


def version_key(version: str) -> tuple:
    """Turn a version string like ``"3.1.3"`` into a comparable tuple.

    ``Unreleased`` sorts newer than any concrete version. Unknown/garbage
    input sorts older than everything.
    """
    if not version:
        return (0,)
    if version.lower() == "unreleased":
        return _UNRELEASED_KEY
    tokens = tuple(int(x) for x in _VERSION_TOKEN_RE.findall(str(version)))
    return tokens or (0,)


def parse_changelog(path: Optional[str] = None) -> List[Dict]:
    """Parse CHANGELOG.md into an ordered (oldest-first) list of release blocks.

    Each block::

        {"title": "3.1.3 — 2026-09-06",
         "version": "3.1.3",
         "date": "2026-09-06",
         "sections": {
            "New Features": ["...", "..."],
            "Bug Fixes": [...],
            "Improvements": [...],
         }}
    """
    path = path or str(CHANGELOG_PATH)
    blocks: List[Dict] = []
    current: Optional[Dict] = None
    current_section = None

    if not os.path.exists(path):
        return blocks

    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n").strip()
        if not line:
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            version = title.split()[0] if title else ""
            date = ""
            if "—" in title:
                date = title.split("—", 1)[1].strip()
            current = {
                "title": title,
                "version": version,
                "date": date,
                "sections": {},
            }
            current_section = None
            blocks.append(current)
        elif line.startswith("### ") and current is not None:
            label = line[4:].strip()
            current["sections"].setdefault(label, [])
            current_section = label
        elif current is not None and current_section:
            sections = current["sections"]
            if line.startswith("- "):
                sections[current_section].append(line[2:].strip().rstrip())
            elif raw[:1].isspace() and sections.get(current_section):
                # Indented continuation of the previous bullet: the changelog
                # wraps long items across several source lines.
                sections[current_section][-1] = (
                    f"{sections[current_section][-1]} {line}".strip())

    return blocks


def whats_new(blocks: List[Dict], last_seen: str, limit: int = 4) -> List[Dict]:
    """Release blocks the user has not seen yet, newest first.

    ``last_seen`` is the last version the user was told about (empty string =
    never, so it starts at the top of the changelog).
    """
    seen_key = version_key(last_seen)
    newer = [b for b in blocks if version_key(b.get("version", "")) > seen_key]
    # Changelog blocks are parsed in file order, which is newest-first.
    return newer[:limit]


def changelog_versions() -> List[str]:
    """Release versions from the changelog, newest first.

    Installed builds have no ``.git`` directory, so the UI uses this list
    as a stand-in for ``git tag``. The ``Unreleased`` heading is skipped
    because it is not a published release.
    """
    return [
        str(block.get("version", ""))
        for block in parse_changelog()
        if block.get("version")
        and str(block["version"]).lower() != "unreleased"
    ]


def _cached_commit_count() -> Optional[int]:
    try:
        with open(REPO_STATS_CACHE, encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - float(data.get("ts", 0)) >= _STATS_TTL:
            return None
        count = int(data.get("commit_count"))
        return count if count >= 0 else None
    except Exception:
        return None


def _store_commit_count(count: int) -> None:
    try:
        os.makedirs(os.path.dirname(REPO_STATS_CACHE), exist_ok=True)
        with open(REPO_STATS_CACHE, "w", encoding="utf-8") as f:
            json.dump({"commit_count": int(count), "ts": time.time()}, f)
    except Exception:
        pass


def commit_count(timeout: float = 5.0) -> Optional[int]:
    """Total commits on the default branch, cached for a day.

    A source checkout uses local ``git`` instead; this is the fallback for
    installed packages (AUR tarballs have no history). Returns ``None`` when
    offline and no fresh cache exists.
    """
    cached = _cached_commit_count()
    if cached is not None:
        return cached
    if os.environ.get("NEOARCH_CHECK_RELEASES", "1") != "1":
        return None
    req = urllib.request.Request(
        _COMMITS_URL,
        headers={
            "User-Agent": f"{APP_NAME} (commit-count check)",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        from neoarch.backend.services.network import urlopen as _urlopen
        with _urlopen(req, timeout=timeout) as resp:
            link = resp.headers.get("Link", "") or ""
            body = resp.read()
    except Exception:
        return None
    match = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link)
    if match:
        count = int(match.group(1))
    else:
        try:
            data = json.loads(body.decode("utf-8"))
            count = len(data) if isinstance(data, list) else 0
        except Exception:
            return None
    _store_commit_count(count)
    return count


def latest_release(timeout: float = 5.0) -> Optional[Dict]:
    """Fetch the newest GitHub release (best-effort).

    Returns ``None`` on any network/parse error so the UI simply stays quiet
    when offline. Result keys: ``version``, ``name``, ``body``, ``html_url``.
    """
    if os.environ.get("NEOARCH_CHECK_RELEASES", "1") != "1":
        return None
    req = urllib.request.Request(
        _RELEASE_URL,
        headers={
            "User-Agent": f"{APP_NAME} (release-info check)",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        from neoarch.backend.services.network import urlopen as _urlopen
        with _urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or not data.get("tag_name"):
        return None
    return {
        "version": str(data["tag_name"]).lstrip("v"),
        "name": str(data.get("name") or str(data["tag_name"])),
        "body": str(data.get("body") or "").strip(),
        "html_url": str(data.get("html_url") or _RELEASE_URL),
    }