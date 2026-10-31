"""Tests for the release-notes service (CHANGELOG parsing / version gates).

Network-dependent GitHub lookups are exercised only through the
NEOARCH_CHECK_RELEASES toggle, which short-circuits to None so tests are
deterministic and offline-safe.
"""

import json
import os
import time

from neoarch.backend.services import release_notes as rn
from neoarch.resources.paths import APP_VERSION


def test_version_key_ordering():
    assert rn.version_key("") == (0,)
    assert rn.version_key("3") < rn.version_key("3.1.2") < rn.version_key("3.1.3")
    assert rn.version_key("v3.1.3") == rn.version_key("3.1.3")
    assert rn.version_key("Unreleased") > rn.version_key("99.0")
    assert rn.version_key("garbage") == (0,)


def test_parse_changelog_joins_wrapped_bullets(tmp_path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text(
        "# Changelog\n\n## 1.0 — 2026-01-01\n\n### New Features\n\n"
        "- **Bold lead.** first part\n"
        "  continues on the next source line and\n"
        "  ends here.\n\n"
        "- second item\n",
        encoding="utf-8")
    blocks = rn.parse_changelog(str(path))
    assert blocks[0]["sections"]["New Features"] == [
        "**Bold lead.** first part continues on the next source line and "
        "ends here.",
        "second item",
    ]


def test_parse_changelog_shapes():
    blocks = rn.parse_changelog()
    assert blocks, "CHANGELOG.md should parse to at least one block"
    for block in blocks:
        assert block["version"]
        assert isinstance(block["sections"], dict)
        assert set(block["sections"]) <= {"New Features", "Bug Fixes", "Improvements"}
        assert all(isinstance(v, list) and v for v in block["sections"].values())
    # Newest-first: on a released build the current header matches APP_VERSION,
    # on a dev build an "Unreleased" section sits on top; either is valid, and
    # subsequent blocks are strictly older.
    assert blocks[0]["version"].lower() == "unreleased" or \
        blocks[0]["version"] == APP_VERSION
    keys = [rn.version_key(b["version"]) for b in blocks]
    assert keys == sorted(keys, reverse=True)


def test_whats_new_only_returns_newer_blocks():
    blocks = rn.parse_changelog()
    seen = "3.1.2"
    out = rn.whats_new(blocks, seen)
    assert out, "should return newer blocks"
    versions = [b["version"] for b in out]
    assert all(rn.version_key(v) > rn.version_key(seen) for v in versions)
    assert versions == list(
        dict.fromkeys(versions)), "no duplicates, newest first"


def test_whats_new_respects_limit():
    blocks = rn.parse_changelog()
    assert len(rn.whats_new(blocks, "", limit=2)) <= 2


def test_latest_release_respects_toggle():
    os.environ["NEOARCH_CHECK_RELEASES"] = "0"
    try:
        assert rn.latest_release() is None
    finally:
        os.environ.pop("NEOARCH_CHECK_RELEASES", None)

def test_changelog_versions_skip_unreleased():
    versions = rn.changelog_versions()
    assert versions
    assert "Unreleased" not in versions
    assert all(v and v.lower() != "unreleased" for v in versions)


def test_commit_count_reads_fresh_cache(tmp_path, monkeypatch):
    cache = tmp_path / "repo-stats.json"
    cache.write_text(json.dumps(
        {"commit_count": 864, "ts": time.time()}), encoding="utf-8")
    monkeypatch.setattr(rn, "REPO_STATS_CACHE", str(cache))
    assert rn.commit_count() == 864


class _FakeResponse:
    headers = {
        "Link": ('<https://api.github.com/repositories/1/commits'
                 '?per_page=1&page=864>; rel="last"')
    }

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"[]"


def test_commit_count_fetches_and_caches(tmp_path, monkeypatch):
    cache = tmp_path / "repo-stats.json"
    monkeypatch.setattr(rn, "REPO_STATS_CACHE", str(cache))
    monkeypatch.setattr(
        "neoarch.backend.services.network.urlopen",
        lambda req, timeout=None: _FakeResponse())
    assert rn.commit_count() == 864
    assert json.loads(cache.read_text(encoding="utf-8"))["commit_count"] == 864
