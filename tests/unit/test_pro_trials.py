"""Tests for local Pro theme trial accounting and tamper handling."""

import json

import pytest

from neoarch.backend.services import pro_trials


@pytest.fixture
def trial_env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return tmp_path / "data" / "neoarch" / "pro_theme_trials.json"


def test_trial_lasts_thirty_minutes_and_cannot_restart(trial_env):
    settings = {}
    now = 1_000_000.0
    ledger = pro_trials.start_trial(
        settings, "neoarch-pro-sakura", now=now)

    assert ledger is not None
    assert settings[pro_trials.TRIAL_SETTING] == ledger
    assert trial_env.exists()

    active = pro_trials.trial_status(
        settings, "neoarch-pro-sakura", now=now + 10)
    assert active.usable
    assert active.remaining == pro_trials.TRIAL_DURATION_SECONDS - 10

    expired = pro_trials.trial_status(
        settings, "neoarch-pro-sakura",
        now=now + pro_trials.TRIAL_DURATION_SECONDS + 1)
    assert expired.state == "expired"
    assert not expired.usable
    assert pro_trials.start_trial(
        settings, "neoarch-pro-sakura", now=now + 60) is None


def test_clock_rollback_is_treated_as_tampering(trial_env):
    settings = {}
    now = 1_000_000.0
    pro_trials.start_trial(settings, "neoarch-pro-moss", now=now)

    status = pro_trials.trial_status(
        settings, "neoarch-pro-moss", now=now - 300)
    assert status.state == "tampered"
    assert pro_trials.start_trial(
        settings, "neoarch-pro-ember", now=now - 300) is None


def test_edited_ledger_is_rejected(trial_env):
    settings = {}
    now = 1_000_000.0
    ledger = pro_trials.start_trial(
        settings, "neoarch-pro-glacier", now=now)
    ledger["themes"]["neoarch-pro-glacier"]["started"] += 60
    trial_env.write_text(json.dumps(ledger), encoding="utf-8")

    status = pro_trials.trial_status(
        settings, "neoarch-pro-glacier", now=now + 10)
    assert status.state == "tampered"
    assert pro_trials.start_trial(
        settings, "neoarch-pro-aero", now=now + 10) is None


def test_backup_restores_trial_after_settings_are_cleared(trial_env):
    settings = {}
    now = 1_000_000.0
    pro_trials.start_trial(settings, "neoarch-pro-lagoon", now=now)

    settings.clear()

    status = pro_trials.trial_status(
        settings, "neoarch-pro-lagoon", now=now + 60)
    assert status.usable
    assert pro_trials.start_trial(
        settings, "neoarch-pro-lagoon", now=now + 60) is None


def test_active_trial_touch_advances_last_seen(trial_env):
    settings = {}
    now = 1_000_000.0
    pro_trials.start_trial(settings, "neoarch-pro-evergreen", now=now)

    touched = pro_trials.touch_trial(settings, now=now + 100)
    assert touched is not None
    assert touched["last_seen"] >= now + 100
    assert pro_trials.trial_status(
        settings, "neoarch-pro-evergreen", now=now + 200).usable
