import hashlib
import json

from neoarch.backend.services import theme_assets
from neoarch.frontend.themes import PRO_UNLOCK_HASHES


class _Response:
    def __init__(self, payload):
        self.headers = {"Content-Length": str(len(payload))}
        self._payload = payload
        self._sent = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        if self._sent:
            return b""
        self._sent = True
        return self._payload


def _entry(theme_id, payload, digest=None):
    return {
        "url": f"https://example.test/{theme_id}.jpg",
        "file": f"{theme_id}.jpg",
        "sha256": digest or hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "version": 1,
    }


def test_manifest_covers_every_locked_pro_theme():
    manifest = json.loads(theme_assets.manifest_path().read_text())
    themes = manifest["themes"]
    assert set(PRO_UNLOCK_HASHES) <= set(themes)
    for theme_id in PRO_UNLOCK_HASHES:
        entry = themes[theme_id]
        assert entry["url"].startswith("https://")
        assert len(entry["sha256"]) == 64
        assert entry["bytes"] > 0
        assert (theme_assets._THEME_DIR / entry["preview"]).is_file()


def test_previews_are_small():
    previews = theme_assets._THEME_DIR / "previews"
    files = list(previews.glob("*.webp"))
    assert len(files) >= len(PRO_UNLOCK_HASHES)
    assert all(path.stat().st_size < 100_000 for path in files)


def test_resolve_path_prefers_valid_cached_wallpaper(tmp_path, monkeypatch):
    payload = b"wallpaper"
    entry = _entry("example", payload)
    monkeypatch.setattr(theme_assets, "_CACHE_ROOT", tmp_path / "data")
    monkeypatch.setattr(theme_assets, "load_manifest", lambda: {"themes": {"example": entry}})
    path = theme_assets.cached_path("example")
    path.parent.mkdir(parents=True)
    path.write_bytes(payload)

    assert theme_assets.resolve_path("example", "/missing/full.jpg") == str(path)


def test_download_writes_verified_wallpaper(tmp_path, monkeypatch):
    payload = b"verified wallpaper"
    entry = _entry("example", payload)
    monkeypatch.setattr(theme_assets, "_CACHE_ROOT", tmp_path / "data")
    monkeypatch.setattr(theme_assets, "_STATE_PATH", tmp_path / "data" / "state.json")
    monkeypatch.setattr(theme_assets, "_TEMP_ROOT", tmp_path / "tmp")
    monkeypatch.setattr(theme_assets, "load_manifest", lambda: {"themes": {"example": entry}})
    monkeypatch.setattr(theme_assets.network, "urlopen", lambda request: _Response(payload))

    path = theme_assets.download("example")

    assert path is not None
    assert path.read_bytes() == payload
    assert theme_assets.is_cached("example")


def test_download_rejects_hash_mismatch(tmp_path, monkeypatch):
    payload = b"tampered wallpaper"
    entry = _entry("example", payload, digest="0" * 64)
    monkeypatch.setattr(theme_assets, "_CACHE_ROOT", tmp_path / "data")
    monkeypatch.setattr(theme_assets, "_STATE_PATH", tmp_path / "data" / "state.json")
    monkeypatch.setattr(theme_assets, "_TEMP_ROOT", tmp_path / "tmp")
    monkeypatch.setattr(theme_assets, "load_manifest", lambda: {"themes": {"example": entry}})
    monkeypatch.setattr(theme_assets.network, "urlopen", lambda request: _Response(payload))

    assert theme_assets.download("example") is None
    assert not theme_assets.cached_path("example").exists()


def test_download_handles_temp_directory_failure(tmp_path, monkeypatch):
    payload = b"wallpaper"
    entry = _entry("example", payload)

    class _BadRoot:
        @staticmethod
        def mkdir(*args, **kwargs):
            raise OSError("cannot create temp directory")

    monkeypatch.setattr(theme_assets, "_CACHE_ROOT", tmp_path / "data")
    monkeypatch.setattr(theme_assets, "_TEMP_ROOT", _BadRoot())
    monkeypatch.setattr(theme_assets, "load_manifest", lambda: {"themes": {"example": entry}})

    assert theme_assets.download("example") is None
    assert "example" not in theme_assets._DOWNLOADING
