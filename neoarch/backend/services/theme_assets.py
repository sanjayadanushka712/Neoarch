import hashlib
import json
import os
import threading
from pathlib import Path
from urllib.request import Request

from neoarch.backend.services import network

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ASSETS_DIR = _PROJECT_ROOT / "assets"
_MANIFEST_PATH = _ASSETS_DIR / "theme-assets.json"
_THEME_DIR = _ASSETS_DIR / "themes"

_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
_CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
_CACHE_ROOT = _DATA_HOME / "neoarch" / "theme-assets"
_STATE_PATH = _CACHE_ROOT / "state.json"
_TEMP_ROOT = _CACHE_HOME / "neoarch" / "theme-assets"

MAX_ASSET_BYTES = 16 * 1024 * 1024
_DOWNLOADING = set()
_DOWNLOAD_LOCK = threading.Lock()


def manifest_path():
    return Path(os.environ.get("NEOARCH_THEME_MANIFEST") or _MANIFEST_PATH)


def cache_root():
    return Path(_CACHE_ROOT)


def load_manifest():
    try:
        with open(manifest_path(), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, TypeError):
        return {"version": 1, "themes": {}}
    themes = data.get("themes")
    if not isinstance(themes, dict):
        return {"version": 1, "themes": {}}
    return data


def get_entry(theme_id):
    entry = load_manifest().get("themes", {}).get(theme_id)
    return dict(entry) if isinstance(entry, dict) else None


def cached_path(theme_id):
    entry = get_entry(theme_id)
    if not entry or not entry.get("file"):
        return None
    return _CACHE_ROOT / theme_id / "backgrounds" / str(entry["file"])


def _state():
    try:
        with open(_STATE_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _save_state(state):
    try:
        _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        temp = _STATE_PATH.with_suffix(".tmp")
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
        os.replace(temp, _STATE_PATH)
    except OSError:
        pass


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_cached(theme_id):
    path = cached_path(theme_id)
    entry = get_entry(theme_id)
    if path is None or entry is None or not path.is_file():
        return False
    expected = str(entry.get("sha256") or "")
    if not expected:
        return False
    try:
        return _sha256(path) == expected
    except OSError:
        return False


def preview_path(theme_id, fallback=None):
    entry = get_entry(theme_id)
    preview = str((entry or {}).get("preview") or "")
    if preview:
        candidate = _THEME_DIR / preview
        if candidate.is_file():
            return str(candidate)
    if fallback:
        candidate = Path(str(fallback))
        if candidate.is_file():
            return str(candidate)
    return ""


def resolve_path(theme_id, fallback=None):
    if is_cached(theme_id):
        return str(cached_path(theme_id))
    if fallback:
        candidate = Path(str(fallback))
        if candidate.is_file():
            return str(candidate)
    preview = preview_path(theme_id)
    return preview or str(fallback or "")


def needs_download(theme_id):
    entry = get_entry(theme_id)
    return bool(entry and entry.get("url") and not is_cached(theme_id))


def _begin(theme_id):
    with _DOWNLOAD_LOCK:
        if theme_id in _DOWNLOADING:
            return False
        _DOWNLOADING.add(theme_id)
        return True


def _end(theme_id):
    with _DOWNLOAD_LOCK:
        _DOWNLOADING.discard(theme_id)


def download(theme_id, progress_cb=None):
    entry = get_entry(theme_id)
    if not entry or not entry.get("url"):
        return None
    if is_cached(theme_id):
        return cached_path(theme_id)
    if not _begin(theme_id):
        return None
    temp = None
    try:
        destination = cached_path(theme_id)
        _TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = _TEMP_ROOT / f"{theme_id}.part"
        expected = str(entry.get("sha256") or "")
        received = 0
        request = Request(entry["url"], headers={"User-Agent": f"neoarch-theme-assets/{entry.get('version', 1)}"})
        with network.urlopen(request) as response:
            total = int(response.headers.get("Content-Length") or 0)
            with open(temp, "wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > MAX_ASSET_BYTES:
                        return None
                    handle.write(chunk)
                    if progress_cb and total:
                        try:
                            progress_cb(received / total)
                        except Exception:
                            pass
        if received <= 0 or _sha256(temp) != expected:
            return None
        os.replace(temp, destination)
        state = _state()
        state[theme_id] = {
            "sha256": expected,
            "bytes": received,
            "version": entry.get("version", 1),
        }
        _save_state(state)
        return destination
    except Exception:
        return None
    finally:
        if temp is not None:
            try:
                temp.unlink(missing_ok=True)
            except Exception:
                pass
        _end(theme_id)


def download_async(theme_id, callback=None):
    def worker():
        path = download(theme_id)
        if callback is not None:
            try:
                callback(theme_id, path)
            except Exception:
                pass
    thread = threading.Thread(target=worker, daemon=True, name=f"theme-asset-{theme_id}")
    thread.start()
    return thread
