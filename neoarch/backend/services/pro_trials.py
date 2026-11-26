"""Local 30-minute Pro theme trials with a tamper-resistant ledger.

Trials are intentionally local-only.  The ledger is HMAC-signed, mirrored to
the user data directory, and rejects clock rollback.  This stops casual edits
and settings deletion, but no offline client can be made truly tamper-proof:
a user who removes every local copy can still start over.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
from pathlib import Path
from typing import NamedTuple

__all__ = [
    "TRIAL_SETTING",
    "TRIAL_DURATION_SECONDS",
    "TrialStatus",
    "load_ledger",
    "start_trial",
    "touch_trial",
    "trial_status",
    "trial_states",
]

TRIAL_SETTING = "pro_theme_trials"
TRIAL_DURATION_SECONDS = 30 * 60
# A small tolerance avoids treating NTP corrections or sub-minute clock drift
# as tampering.
_CLOCK_ROLLBACK_TOLERANCE_SECONDS = 120
_LEDGER_VERSION = 1
# This key makes casual JSON edits detectable.  It is not a substitute for a
# server-side entitlement check.
_LEDGER_KEY = bytes.fromhex(
    "5e2a360dae5e767e86c77b9c869c9cf3"
    "a330d433da7ee26db57ffaf964c04965"
)


class TrialStatus(NamedTuple):
    state: str
    remaining: int

    @property
    def usable(self) -> bool:
        return self.state == "active"


def _backup_path() -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(base) / "neoarch" / "pro_theme_trials.json"


def _machine_id() -> str:
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                value = handle.read().strip()
            if value:
                return value
        except OSError:
            continue
    return ""


def _signing_key() -> bytes:
    return hmac.new(
        _LEDGER_KEY,
        _machine_id().encode("utf-8"),
        hashlib.sha256,
    ).digest()


def _clean_time(value) -> float:
    return round(float(value), 6)


def _payload(last_seen: float, themes: dict) -> bytes:
    body = {
        "version": _LEDGER_VERSION,
        "last_seen": _clean_time(last_seen),
        "themes": {
            theme_id: {"started": _clean_time(record["started"])}
            for theme_id, record in sorted(themes.items())
        },
    }
    return json.dumps(
        body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _make_ledger(themes: dict, last_seen: float) -> dict:
    clean_themes = {
        str(theme_id): {"started": _clean_time(record["started"])}
        for theme_id, record in sorted(themes.items())
    }
    clean_last_seen = _clean_time(last_seen)
    signature = hmac.new(
        _signing_key(),
        _payload(clean_last_seen, clean_themes),
        hashlib.sha256,
    ).hexdigest()
    return {
        "version": _LEDGER_VERSION,
        "last_seen": clean_last_seen,
        "themes": clean_themes,
        "signature": signature,
    }


def _decode_ledger(value) -> dict | None:
    if not isinstance(value, dict) or value.get("version") != _LEDGER_VERSION:
        return None
    themes = value.get("themes")
    if not isinstance(themes, dict):
        return None
    try:
        last_seen = _clean_time(value.get("last_seen", 0))
    except (TypeError, ValueError):
        return None
    clean_themes = {}
    for theme_id, record in themes.items():
        if not isinstance(theme_id, str) or not isinstance(record, dict):
            return None
        try:
            started = _clean_time(record.get("started"))
        except (TypeError, ValueError):
            return None
        if started < 0:
            return None
        clean_themes[theme_id] = {"started": started}
    expected = hmac.new(
        _signing_key(),
        _payload(last_seen, clean_themes),
        hashlib.sha256,
    ).hexdigest()
    signature = value.get("signature")
    if not isinstance(signature, str) or not hmac.compare_digest(
            signature, expected):
        return None
    return _make_ledger(clean_themes, last_seen)


def _read_backup(path: Path | None = None):
    try:
        with open(path or _backup_path(), "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _write_backup(ledger: dict, path: Path | None = None) -> None:
    target = path or _backup_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(ledger, handle, sort_keys=True, separators=(",", ":"))
        os.replace(temporary, target)
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
    except OSError:
        pass


def _merge(left: dict, right: dict) -> dict:
    themes = dict(left["themes"])
    for theme_id, record in right["themes"].items():
        current = themes.get(theme_id)
        if current is None or record["started"] < current["started"]:
            themes[theme_id] = record
    last_seen = max(left["last_seen"], right["last_seen"])
    return _make_ledger(themes, last_seen)


def load_ledger(settings: dict, backup_path: Path | None = None):
    """Return ``(ledger, tampered)`` without mutating settings.

    The mirrored copy is merged with the settings copy so deleting just one
    of them does not reset trials.  A non-empty but invalid ledger is treated
    as tampering and disables further trials.
    """
    raw_stored = settings.get(TRIAL_SETTING) if isinstance(settings, dict) else None
    raw_backup = _read_backup(backup_path)
    stored = _decode_ledger(raw_stored) if raw_stored else None
    backup = _decode_ledger(raw_backup) if raw_backup else None

    if stored is None and backup is None:
        if raw_stored or raw_backup:
            return _make_ledger({}, 0), True
        return _make_ledger({}, 0), False
    if stored is None:
        return backup, False
    if backup is None:
        return stored, False
    return _merge(stored, backup), False


def _clock_tampered(ledger: dict, now: float) -> bool:
    return now + _CLOCK_ROLLBACK_TOLERANCE_SECONDS < ledger["last_seen"]


def _status(ledger: dict, tampered: bool, theme_id: str, now: float) -> TrialStatus:
    if tampered or _clock_tampered(ledger, now):
        return TrialStatus("tampered", 0)
    record = ledger["themes"].get(theme_id)
    if record is None:
        return TrialStatus("available", TRIAL_DURATION_SECONDS)
    started = record["started"]
    if now + _CLOCK_ROLLBACK_TOLERANCE_SECONDS < started:
        return TrialStatus("tampered", 0)
    elapsed = max(0.0, now - started)
    remaining = TRIAL_DURATION_SECONDS - elapsed
    if remaining <= 0:
        return TrialStatus("expired", 0)
    return TrialStatus("active", int(math.ceil(remaining)))


def trial_states(settings: dict, theme_ids, now=None,
                 backup_path: Path | None = None) -> dict:
    """Return trial statuses for several themes with one ledger read."""
    import time

    current = float(time.time() if now is None else now)
    ledger, tampered = load_ledger(settings, backup_path)
    return {
        theme_id: _status(ledger, tampered, theme_id, current)
        for theme_id in theme_ids
    }


def trial_status(settings: dict, theme_id: str, now=None,
                 backup_path: Path | None = None) -> TrialStatus:
    return trial_states(settings, (theme_id,), now, backup_path)[theme_id]


def start_trial(settings: dict, theme_id: str, now=None,
                backup_path: Path | None = None) -> dict | None:
    """Start a one-time trial and return the signed ledger, or ``None``."""
    import time

    current = float(time.time() if now is None else now)
    ledger, tampered = load_ledger(settings, backup_path)
    if tampered or _clock_tampered(ledger, current):
        return None
    if theme_id in ledger["themes"]:
        return None
    ledger["themes"][theme_id] = {"started": _clean_time(current)}
    ledger = _make_ledger(
        ledger["themes"], max(ledger["last_seen"], current))
    _write_backup(ledger, backup_path)
    if isinstance(settings, dict):
        settings[TRIAL_SETTING] = ledger
    return ledger


def touch_trial(settings: dict, now=None,
                backup_path: Path | None = None) -> dict | None:
    """Refresh the signed last-seen timestamp while a trial is active."""
    import time

    current = float(time.time() if now is None else now)
    ledger, tampered = load_ledger(settings, backup_path)
    if tampered or _clock_tampered(ledger, current):
        return None
    active = any(
        current - record["started"] < TRIAL_DURATION_SECONDS
        for record in ledger["themes"].values()
    )
    if not active:
        return None
    ledger = _make_ledger(
        ledger["themes"], max(ledger["last_seen"], current))
    _write_backup(ledger, backup_path)
    if isinstance(settings, dict):
        settings[TRIAL_SETTING] = ledger
    return ledger
