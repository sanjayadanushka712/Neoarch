import json
import re
from pathlib import Path

import pytest

from neoarch.frontend import themes
from neoarch.frontend.tokens import icon_tint
from neoarch.frontend.themes import (
    BUILTIN_THEME_DIR,
    DEFAULT_THEME_ID,
    SYSTEM_THEME_ID,
    THEMES,
    ThemeManager,
    FREE_PRO_THEMES,
    PRO_UNLOCK_HASHES,
    UNLOCKED_PRO_SETTING,
    brand_assets_for_theme,
    get_theme_background,
    get_theme_data,
    get_theme_effects,
    is_theme_locked,
    load_themes,
    normalise_unlocked_themes,
    theme_glow_enabled,
    verify_theme_unlock_code,
)


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _write_theme(directory, filename, data):
    path = directory / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_builtin_themes_load():
    themes = load_themes([BUILTIN_THEME_DIR])

    assert set(themes) == {
        "dark", "light", "dracula", "nord",
        "solarized-dark", "forest-green", "neoarch-pro",
        "neoarch-pro-evergreen", "neoarch-pro-ember",
        "neoarch-pro-glacier", "neoarch-pro-aero",
        "neoarch-pro-lagoon", "neoarch-pro-moss",
        "neoarch-pro-sakura", "neoarch-pro-crystal",
        "neoarch-pro-endeavour", "neoarch-pro-v4",
        "neoarch-pro-halloween",
    }
    assert themes["dark"]["colors"]["BG"] == "#0C0C0E"
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", themes["light"]["colors"]["BG"])
    assert themes["light"]["is_dark"] is False


def test_pro_theme_background_metadata_is_loaded():
    themes = load_themes([BUILTIN_THEME_DIR])
    pro = themes["neoarch-pro"]

    assert pro["tier"] == "pro"
    assert pro["background"]["blur"] == 22
    assert Path(pro["background"]["image"]).is_file()


@pytest.mark.parametrize("theme_id, accent, is_dark", [
    ("neoarch-pro-evergreen", "#67AB7C", True),
    ("neoarch-pro-ember", "#E1A866", True),
    ("neoarch-pro-glacier", "#4F7899", False),
    ("neoarch-pro-aero", "#42AFCB", True),
    ("neoarch-pro-lagoon", "#66BED2", True),
    ("neoarch-pro-moss", "#9FB87C", True),
    ("neoarch-pro-sakura", "#C48DD8", True),
    ("neoarch-pro-crystal", "#4DAEAB", True),
    ("neoarch-pro-endeavour", "#9B6BFF", True),
    ("neoarch-pro-v4", "#62E6D4", True),
    ("neoarch-pro-halloween", "#F08A24", True),
])
def test_pro_theme_has_background_and_brand_artwork(theme_id, accent, is_dark):
    themes = load_themes([BUILTIN_THEME_DIR])
    pro = themes[theme_id]

    assert pro["tier"] == "pro"
    assert pro["brand_icon"] == f"app/icon-pro-{theme_id.rsplit('-', 1)[-1]}"
    assert pro["brand_logo"] == f"app/logo-pro-{theme_id.rsplit('-', 1)[-1]}"
    assert Path(pro["background"]["image"]).is_file()
    assert pro["colors"]["ACCENT"] == accent
    assert pro["is_dark"] is is_dark


def test_brand_assets_honour_any_theme_tier():
    assert brand_assets_for_theme({
        "tier": "standard",
        "brand_icon": "custom/icon",
        "brand_logo": "custom/logo",
    }) == ("custom/icon", "custom/logo")
    assert brand_assets_for_theme({"tier": "pro"}) == (
        "app/icon-pro", "app/logo-pro")
    assert brand_assets_for_theme({"tier": "standard"}) == ("", "")
    assert brand_assets_for_theme(None) == ("", "")


def test_custom_theme_brand_assets_resolve_next_to_json(tmp_path):
    icon = tmp_path / "custom-icon.png"
    logo = tmp_path / "custom-logo.png"
    icon.write_bytes(b"icon")
    logo.write_bytes(b"logo")
    (tmp_path / "custom.json").write_text(json.dumps({
        "id": "custom",
        "brand_icon": "custom-icon.png",
        "brand_logo": "custom-logo.png",
    }), encoding="utf-8")

    theme = load_themes([tmp_path])["custom"]

    assert theme["brand_icon"] == str(icon)
    assert theme["brand_logo"] == str(logo)


@pytest.mark.parametrize("theme_id", [
    "neoarch-pro",
    "neoarch-pro-evergreen",
    "neoarch-pro-ember",
    "neoarch-pro-glacier",
    "neoarch-pro-aero",
    "neoarch-pro-lagoon",
    "neoarch-pro-moss",
    "neoarch-pro-sakura",
    "neoarch-pro-crystal",
    "neoarch-pro-endeavour",
    "neoarch-pro-v4",
    "neoarch-pro-halloween",
])
def test_pro_themes_define_glow_effects(theme_id):
    theme = get_theme_data(theme_id)
    effects = get_theme_effects(theme_id)

    assert effects is not None
    assert effects["glow"]["enabled"] is True
    assert effects["glow"]["color"] == theme["colors"]["ACCENT"]
    assert 0.5 <= effects["glow"]["width"] <= 4.0
    assert 0.0 <= effects["glow"]["opacity"] <= 1.0
    assert theme_glow_enabled(theme_id) is True
    assert get_theme_effects("dark") is None
    assert theme_glow_enabled("dark") is False


def test_pro_theme_tints_stroke_icons(tmp_path, qapp):
    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    try:
        assert manager.apply_theme("neoarch-pro")
        assert icon_tint() == "#D9C6FF"
    finally:
        manager.apply_theme("dark")


def test_background_image_path_resolves_relative_to_theme(tmp_path):
    _write_theme(tmp_path, "custom-pro.json", {
        "id": "custom-pro",
        "tier": "pro",
        "background": {"image": "art/background.jpg"},
    })

    themes = load_themes([BUILTIN_THEME_DIR, tmp_path])

    assert themes["custom-pro"]["background"]["image"] == str(
        tmp_path / "art" / "background.jpg")


def test_free_pro_themes_apply_and_other_pro_themes_are_locked(tmp_path, qapp):
    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    try:
        assert FREE_PRO_THEMES == {
            "neoarch-pro",
            "neoarch-pro-endeavour",
            "neoarch-pro-v4",
        }
        assert manager.apply_theme("neoarch-pro")
        assert get_theme_background("neoarch-pro")["blur"] == 22
        assert manager.apply_theme("neoarch-pro-endeavour")
        assert manager.current_id == "neoarch-pro-endeavour"
        assert manager.apply_theme("neoarch-pro-v4")
        assert manager.current_id == "neoarch-pro-v4"

        for theme_id in THEMES:
            if get_theme_data(theme_id).get("tier") != "pro":
                continue
            if theme_id in FREE_PRO_THEMES:
                continue
            assert is_theme_locked(theme_id)
            assert not manager.apply_theme(theme_id)
            assert manager.current_id == "neoarch-pro-v4"

        assert get_theme_background(SYSTEM_THEME_ID) is None
    finally:
        manager.apply_theme("dark")


def test_standard_and_free_pro_themes_are_not_locked():
    for theme_id in ("dark", "light", "dracula", "neoarch-pro",
                     "neoarch-pro-endeavour", "neoarch-pro-v4"):
        assert not is_theme_locked(theme_id)


def test_partial_user_theme_inherits_dark(tmp_path):
    _write_theme(tmp_path, "custom.json", {
        "id": "custom",
        "name": "Custom",
        "colors": {"ACCENT": "#123456"},
    })

    themes = load_themes([BUILTIN_THEME_DIR, tmp_path])

    assert themes["custom"]["name"] == "Custom"
    assert themes["custom"]["colors"]["ACCENT"] == "#123456"
    assert themes["custom"]["colors"]["BG"] == themes["dark"]["colors"]["BG"]
    assert themes["custom"]["source_colors"] == themes["dark"]["source_colors"]


def test_later_directories_override_earlier_ones(tmp_path):
    _write_theme(tmp_path, "light.json", {
        "id": "light",
        "name": "Light Override",
        "colors": {"BG": "#FFFFFF"},
    })

    themes = load_themes([BUILTIN_THEME_DIR, tmp_path])

    assert themes["light"]["name"] == "Light Override"
    assert themes["light"]["colors"]["BG"] == "#FFFFFF"


def test_invalid_theme_files_are_skipped(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    _write_theme(tmp_path, "bad-colors.json", {
        "id": "bad",
        "colors": ["not", "a", "dict"],
    })

    themes = load_themes([BUILTIN_THEME_DIR, tmp_path])

    assert "broken" not in themes
    assert "bad" not in themes


def test_system_theme_follows_os_and_persists_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    try:
        assert manager.apply_theme(SYSTEM_THEME_ID)
        assert manager.current_id == SYSTEM_THEME_ID
        assert manager.resolved_id == "light"
        assert json.loads((tmp_path / "theme.json").read_text())["theme"] == "system"
    finally:
        manager.apply_theme("dark")


def test_system_theme_display_data_uses_resolved_palette(monkeypatch):
    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    monkeypatch.setattr(
        themes, "_system_palette_colors",
        lambda base: dict(base["colors"]))

    data = get_theme_data(SYSTEM_THEME_ID)

    assert data["name"] == "System"
    assert data["colors"]["BG"] == THEMES["light"]["colors"]["BG"]


def test_system_theme_uses_live_palette_roles(monkeypatch):
    from PyQt6.QtGui import QColor, QPalette
    from PyQt6.QtWidgets import QApplication

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#292A2D"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#35363A"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#3C4043"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#E8EAED"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#F1F3F4"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#8AB4F8"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9AA0A6"))

    class _App:
        def palette(self):
            return palette

    monkeypatch.setattr(
        QApplication, "instance", staticmethod(lambda: _App()))
    monkeypatch.setattr(themes, "system_theme_id", lambda: "dark")

    data = get_theme_data(SYSTEM_THEME_ID)
    colors = data["colors"]

    assert data["is_dark"] is True
    assert colors["BG"] == "#202124"
    assert colors["SURFACE"] == "#292A2D"
    assert colors["TEXT"] == "#F1F3F4"
    assert colors["TEXT_ON_ACCENT"] == "#202124"
    assert colors["ACCENT"] == "#8AB4F8"
    assert colors["NEON"] == "#8AB4F8"
    assert colors["BORDER_FOCUS"] == "rgba(138, 180, 248, 0.550)"
    assert colors["OVERLAY_06"] == "rgba(232, 234, 237, 0.060)"
    assert colors["ACCENT_08"] == "rgba(138, 180, 248, 0.080)"


def test_system_font_families_use_os_fonts(monkeypatch):
    from PyQt6.QtGui import QFont, QFontDatabase
    from PyQt6.QtWidgets import QApplication

    class _App:
        def font(self):
            return QFont("Fake UI")

    monkeypatch.setattr(
        QApplication, "instance", staticmethod(lambda: _App()))

    def _system_font(kind):
        if kind == QFontDatabase.SystemFont.FixedFont:
            return QFont("Test Mono")
        return QFont("Test Sans")

    monkeypatch.setattr(
        QFontDatabase, "systemFont", staticmethod(_system_font))

    families = themes.system_font_families()

    assert families is not None
    assert families[0].startswith("'Test Sans'")
    assert families[1].startswith("'Test Mono'")


def test_manager_applies_system_fonts_and_restores_defaults(
        tmp_path, monkeypatch):
    from neoarch.frontend import tokens

    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    monkeypatch.setattr(
        themes, "system_font_families",
        lambda: ("'Test Sans', sans-serif", "'Test Mono', monospace"))
    monkeypatch.setattr(themes, "system_font_scale", lambda: 1.0)

    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    try:
        assert manager.apply_theme(SYSTEM_THEME_ID)
        assert tokens.Fonts.FAMILY == "'Test Sans', sans-serif"
        assert tokens.Fonts.MONO == "'Test Mono', monospace"
        assert tokens.Fonts.BASE == "13px"
    finally:
        manager.apply_theme("dark")

    assert tokens.Fonts.FAMILY == tokens.Fonts.DEFAULT_FAMILY
    assert tokens.Fonts.MONO == tokens.Fonts.DEFAULT_MONO


def test_manager_applies_system_metrics_and_restores_defaults(
        tmp_path, monkeypatch):
    from neoarch.frontend import tokens

    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    monkeypatch.setattr(themes, "system_metric_scale", lambda: 0.85)
    monkeypatch.setattr(themes, "system_scrollbar_width", lambda: 12)

    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    try:
        assert manager.apply_theme(SYSTEM_THEME_ID)
        assert tokens.Radii.SM == "3"
        assert tokens.Radii.MD == "7"
        assert tokens.Spacing.SM == "7"
        assert tokens.Scrollbar.WIDTH == "12"
        assert tokens.Scrollbar.RADIUS == "6"
        assert tokens.Scrollbar.MARGIN == "3"
        assert tokens.Scrollbar.MIN_LEN == "36"
    finally:
        manager.apply_theme("dark")

    assert tokens.Radii.SM == tokens.DEFAULT_RADII["SM"]
    assert tokens.Radii.MD == tokens.DEFAULT_RADII["MD"]
    assert tokens.Spacing.SM == tokens.DEFAULT_SPACING["SM"]
    assert tokens.Scrollbar.WIDTH == tokens.DEFAULT_SCROLLBAR["WIDTH"]
    assert tokens.Scrollbar.RADIUS == tokens.DEFAULT_SCROLLBAR["RADIUS"]
    assert tokens.Scrollbar.MARGIN == tokens.DEFAULT_SCROLLBAR["MARGIN"]
    assert tokens.Scrollbar.MIN_LEN == tokens.DEFAULT_SCROLLBAR["MIN_LEN"]


def test_failed_theme_application_restores_tokens(
        tmp_path, monkeypatch, qapp):
    from neoarch.frontend import tokens

    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    assert manager.apply_theme("dark")
    baseline = {
        "bg": tokens.Colors.BG,
        "radii_sm": tokens.Radii.SM,
        "spacing_sm": tokens.Spacing.SM,
        "scrollbar": tokens.Scrollbar.WIDTH,
    }

    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")
    monkeypatch.setattr(themes, "system_metric_scale", lambda: 0.5)
    monkeypatch.setattr(themes, "system_scrollbar_width", lambda: 14)

    def _fail():
        raise RuntimeError("stylesheet failed")

    monkeypatch.setattr(tokens.QSS, "regenerate", _fail)
    with pytest.raises(RuntimeError):
        manager.apply_theme(SYSTEM_THEME_ID)

    assert manager.current_id == "dark"
    assert tokens.Colors.BG == baseline["bg"]
    assert tokens.Radii.SM == baseline["radii_sm"]
    assert tokens.Spacing.SM == baseline["spacing_sm"]
    assert tokens.Scrollbar.WIDTH == baseline["scrollbar"]


def test_system_change_is_debounced(tmp_path, qapp, monkeypatch):
    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "theme.json")
    manager._current_id = SYSTEM_THEME_ID
    calls = []
    monkeypatch.setattr(
        manager, "apply_theme",
        lambda theme_id: calls.append(theme_id) or True)

    manager._on_system_color_scheme_changed()

    assert calls == []
    assert manager._system_update_timer.isActive()

    manager._apply_system_update()

    assert calls == [SYSTEM_THEME_ID]


def test_system_palette_raises_low_contrast_borders(monkeypatch, qapp):
    from PyQt6.QtGui import QColor, QPalette
    from PyQt6.QtWidgets import QApplication

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#EEEEEE"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#EEEEEE"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3355FF"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#DDDDDD"))

    class _App:
        def palette(self):
            return palette

    monkeypatch.setattr(
        QApplication, "instance", staticmethod(lambda: _App()))
    monkeypatch.setattr(themes, "system_theme_id", lambda: "light")

    border = get_theme_data(SYSTEM_THEME_ID)["colors"]["BORDER"]
    alpha = float(re.search(r", ([0-9.]+)\)$", border).group(1))

    assert alpha > 0.10


def test_load_saved_defaults_to_endeavour(tmp_path):
    manager = ThemeManager()
    manager._settings_path = str(tmp_path / "missing.json")
    try:
        manager.load_saved()
        assert DEFAULT_THEME_ID == "neoarch-pro-endeavour"
        assert manager.current_id == DEFAULT_THEME_ID
        assert manager.resolved_id == DEFAULT_THEME_ID
    finally:
        manager.apply_theme("dark")


def test_system_theme_uses_palette_when_color_scheme_unknown(monkeypatch):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QPalette
    from PyQt6.QtWidgets import QApplication

    class _Hints:
        def colorScheme(self):
            return Qt.ColorScheme.Unknown

    class _Palette:
        def color(self, role):
            assert role == QPalette.ColorRole.Window
            return QColor("#FFFFFF")

    class _App:
        def styleHints(self):
            return _Hints()

        def palette(self):
            return _Palette()

    monkeypatch.setattr(QApplication, "instance", staticmethod(lambda: _App()))

    assert themes.system_theme_id() == "light"


def test_locked_pro_themes_store_only_salted_password_hashes():
    locked = {
        theme_id for theme_id, theme in THEMES.items()
        if theme.get("tier") == "pro" and theme_id not in FREE_PRO_THEMES
    }

    assert set(PRO_UNLOCK_HASHES) == locked
    for theme_id, encoded in PRO_UNLOCK_HASHES.items():
        assert is_theme_locked(theme_id)
        scheme, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        assert scheme == "pbkdf2_sha256"
        assert int(iterations) >= 600_000
        assert len(bytes.fromhex(salt_hex)) == 16
        assert len(bytes.fromhex(digest_hex)) == 32
        assert not verify_theme_unlock_code(theme_id, "wrong-code")


def test_unlock_password_is_verified_against_pbkdf2_hash(monkeypatch):
    import hashlib

    password = "TestOnly-Crystal-123"
    salt = bytes.fromhex("00112233445566778899aabbccddeeff")
    iterations = 1_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations)
    encoded = f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"
    monkeypatch.setitem(
        themes.PRO_UNLOCK_HASHES, "neoarch-pro-crystal", encoded)

    assert verify_theme_unlock_code("neoarch-pro-crystal", password)
    assert verify_theme_unlock_code("neoarch-pro-crystal", f" {password} ")
    assert not verify_theme_unlock_code(
        "neoarch-pro-crystal", password.lower())
    assert not verify_theme_unlock_code("neoarch-pro-crystal", "")
    assert not verify_theme_unlock_code("neoarch-pro-ember", password)


def test_unlocked_pro_theme_can_be_applied(tmp_path, qapp):
    from PyQt6.QtCore import QObject

    class _Owner(QObject):
        def __init__(self):
            super().__init__()
            self.settings = {
                UNLOCKED_PRO_SETTING: ["neoarch-pro-ember"],
            }

    owner = _Owner()
    manager = ThemeManager(owner)
    manager._settings_path = str(tmp_path / "theme.json")
    try:
        assert manager.apply_theme("neoarch-pro-ember")
        assert manager.current_id == "neoarch-pro-ember"
        assert not manager.apply_theme("neoarch-pro-crystal")
    finally:
        manager.apply_theme("dark")


def test_pro_theme_trial_allows_apply_until_expiry(
        tmp_path, qapp, monkeypatch):
    import time
    from PyQt6.QtCore import QObject
    from neoarch.backend.services import pro_trials

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    class _Owner(QObject):
        def __init__(self):
            super().__init__()
            self.settings = {UNLOCKED_PRO_SETTING: []}

    now = time.time()
    active_owner = _Owner()
    pro_trials.start_trial(
        active_owner.settings, "neoarch-pro-sakura", now=now)
    active_manager = ThemeManager(active_owner)
    active_manager._settings_path = str(tmp_path / "active-theme.json")

    expired_owner = _Owner()
    pro_trials.start_trial(
        expired_owner.settings, "neoarch-pro-ember",
        now=now - pro_trials.TRIAL_DURATION_SECONDS - 1)
    expired_manager = ThemeManager(expired_owner)
    expired_manager._settings_path = str(tmp_path / "expired-theme.json")
    try:
        assert active_manager.apply_theme("neoarch-pro-sakura")
        assert active_manager.current_id == "neoarch-pro-sakura"
        assert not expired_manager.apply_theme("neoarch-pro-ember")
    finally:
        active_manager.apply_theme("dark")


def test_unlocked_theme_setting_is_normalised():
    assert normalise_unlocked_themes("neoarch-pro-moss") == {
        "neoarch-pro-moss"}
    assert normalise_unlocked_themes([
        " neoarch-pro-moss ", "", None, "neoarch-pro-aero",
    ]) == {"neoarch-pro-moss", "neoarch-pro-aero"}
    assert normalise_unlocked_themes(None) == frozenset()


def test_theme_manager_reads_unlocked_settings_before_app_is_ready(
        tmp_path, qapp, monkeypatch):
    from PyQt6.QtCore import QObject
    from neoarch.backend.services import settings as settings_service

    owner = QObject()
    manager = ThemeManager(owner)
    manager._settings_path = str(tmp_path / "theme.json")
    monkeypatch.setattr(
        settings_service, "load_settings",
        lambda: {UNLOCKED_PRO_SETTING: ["neoarch-pro-sakura"]})
    try:
        assert manager.apply_theme("neoarch-pro-sakura")
        assert manager.current_id == "neoarch-pro-sakura"
    finally:
        manager.apply_theme("dark")
