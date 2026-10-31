"""Tests for Flathub AppStream screenshot lookup."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import neoarch.backend.services.screenshots as screenshots  # noqa: E402


class _Response:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_urlopen(monkeypatch, payload, calls):
    def fake_urlopen(request, timeout=0):
        calls.append(request.full_url)
        return _Response(payload)

    monkeypatch.setattr(screenshots.urllib.request, "urlopen", fake_urlopen)


def test_empty_app_id_skips_network(monkeypatch):
    calls = []
    _patch_urlopen(monkeypatch, {}, calls)
    assert screenshots.flathub_screenshots("") == []
    assert calls == []


def test_picks_largest_fitting_size(monkeypatch):
    screenshots.clear_cache()
    calls = []
    payload = {
        "screenshots": [
            {"caption": "Main", "sizes": [
                {"src": "https://x/small.png", "width": "224"},
                {"src": "https://x/large.png", "width": "624"},
                {"src": "https://x/huge.png", "width": "1600"},
            ]},
        ]
    }
    _patch_urlopen(monkeypatch, payload, calls)
    slides = screenshots.flathub_screenshots("org.example.App")
    assert slides == [{"caption": "Main",
                       "url": "https://x/large.png"}]
    assert calls and "org.example.App" in calls[0]


def test_falls_back_to_smallest_when_all_oversized(monkeypatch):
    screenshots.clear_cache()
    payload = {"screenshots": [
        {"caption": "", "sizes": [
            {"src": "https://x/a.png", "width": "1200"},
            {"src": "https://x/b.png", "width": "1600"},
        ]},
    ]}
    _patch_urlopen(monkeypatch, payload, [])
    slides = screenshots.flathub_screenshots("org.example.Big")
    assert slides[0]["url"] == "https://x/a.png"


def test_results_are_cached(monkeypatch):
    screenshots.clear_cache()
    calls = []
    payload = {"screenshots": [
        {"caption": "One", "sizes": [{"src": "https://x/1.png",
                                      "width": "500"}]},
    ]}
    _patch_urlopen(monkeypatch, payload, calls)
    first = screenshots.flathub_screenshots("org.example.Cached")
    second = screenshots.flathub_screenshots("org.example.Cached")
    assert first == second
    assert len(calls) == 1
    screenshots.flathub_screenshots("org.example.Cached", refresh=True)
    assert len(calls) == 2


def test_network_failure_returns_empty_and_caches(monkeypatch):
    screenshots.clear_cache()
    calls = []

    def boom(request, timeout=0):
        calls.append(request.full_url)
        raise OSError("offline")

    monkeypatch.setattr(screenshots.urllib.request, "urlopen", boom)
    assert screenshots.flathub_screenshots("org.example.Offline") == []
    assert screenshots.flathub_screenshots("org.example.Offline") == []
    assert len(calls) == 1


def test_missing_screenshots_returns_empty(monkeypatch):
    screenshots.clear_cache()
    _patch_urlopen(monkeypatch, {"screenshots": None}, [])
    assert screenshots.flathub_screenshots("org.example.None") == []


def test_entries_without_src_are_skipped(monkeypatch):
    screenshots.clear_cache()
    payload = {"screenshots": [
        {"caption": "bad", "sizes": [{"width": "500"}]},
        {"caption": "good", "sizes": [{"src": "https://x/g.png",
                                       "width": "500"}]},
    ]}
    _patch_urlopen(monkeypatch, payload, [])
    slides = screenshots.flathub_screenshots("org.example.Mixed")
    assert slides == [{"caption": "good", "url": "https://x/g.png"}]
