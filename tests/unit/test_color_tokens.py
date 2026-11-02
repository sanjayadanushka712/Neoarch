import ast
import re
from pathlib import Path

from neoarch.frontend import tokens
from neoarch.frontend.styles import Styles
from neoarch.frontend.themes import (
    BUILTIN_THEME_DIR,
    THEMES,
    ThemeManager,
    load_themes,
)


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "neoarch" / "frontend"
COLOR_LITERAL = re.compile(
    r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b"
    r"|rgba?\([^){}]*\)"
)
TOKEN_REF = re.compile(r"\b(Colors|Fonts|Radii|Spacing)\.([A-Z0-9_]+)\b")
DOUBLED_TOKEN_REF = re.compile(
    r"\{\{(?:Colors|Fonts|Radii|Spacing)\."
)
ALLOWED = {"tokens.py", "styles.py"}


def test_frontend_colors_come_from_tokens():
    offenders = {}
    for path in FRONTEND_DIR.rglob("*.py"):
        if path.name in ALLOWED:
            continue
        hits = COLOR_LITERAL.findall(path.read_text(encoding="utf-8"))
        if hits:
            offenders[str(path.relative_to(FRONTEND_DIR))] = sorted(set(hits))

    assert not offenders, offenders


def test_builtin_themes_are_selectable():
    themes = load_themes([BUILTIN_THEME_DIR])

    for theme_id in ("dark", "light", "dracula", "nord"):
        assert not themes[theme_id].get("coming_soon")


def test_theme_switch_updates_tokens_and_generated_styles(monkeypatch):
    manager = ThemeManager()
    monkeypatch.setattr(manager, "_save", lambda: None)
    try:
        for theme_id in ("light", "dracula", "nord"):
            assert manager.apply_theme(theme_id)
            colors = THEMES[theme_id]["colors"]
            assert tokens.Colors.BG == colors["BG"]
            bg = tokens.qcolor(colors["BG"])
            assert f"rgba({bg.red()}, {bg.green()}, {bg.blue()}," in tokens.DARK_STYLESHEET
            assert colors["SURFACE"].lower() in Styles.card().lower()
            assert colors["TEXT"].lower() in Styles.text().lower()
            assert tokens.qcolor(tokens.Colors.OVERLAY_12).isValid()
    finally:
        manager.apply_theme("dark")


def test_white_button_uses_text_on_white_token(monkeypatch):
    manager = ThemeManager()
    monkeypatch.setattr(manager, "_save", lambda: None)
    try:
        assert manager.apply_theme("light")
        color_lines = [
            line.strip()
            for line in Styles.btn_white().splitlines()
            if line.strip().startswith("color:")
        ]
        assert f"color: {tokens.Colors.TEXT_ON_WHITE};" in color_lines
        assert f"color: {tokens.Colors.TEXT_ON_ACCENT};" not in color_lines
    finally:
        manager.apply_theme("dark")


def test_frontend_token_references_exist():
    classes = {
        "Colors": tokens.Colors,
        "Fonts": tokens.Fonts,
        "Radii": tokens.Radii,
        "Spacing": tokens.Spacing,
    }
    missing = {}
    doubled = {}
    for path in FRONTEND_DIR.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(FRONTEND_DIR))
        hits = DOUBLED_TOKEN_REF.findall(source)
        if hits:
            doubled[relative] = len(hits)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in classes
            ):
                if not hasattr(classes[node.value.id], node.attr):
                    missing.setdefault(relative, set()).add(
                        f"{node.value.id}.{node.attr} @ {node.lineno}"
                    )
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for class_name, attr in TOKEN_REF.findall(node.value):
                    if not hasattr(classes[class_name], attr):
                        missing.setdefault(relative, set()).add(
                            f"{class_name}.{attr} in string @ {node.lineno}"
                        )

    assert not missing, missing
    assert not doubled, doubled


def test_builtin_themes_define_all_color_tokens():
    token_names = {
        name
        for name, value in vars(tokens.Colors).items()
        if name.isupper() and isinstance(value, str)
    }
    for theme_id in ("dark", "light", "dracula", "nord"):
        missing = token_names - set(THEMES[theme_id]["colors"])
        assert not missing, (theme_id, sorted(missing))

def test_window_background_tracks_theme(monkeypatch):
    manager = ThemeManager()
    monkeypatch.setattr(manager, "_save", lambda: None)
    try:
        for theme_id in ("light", "dracula", "nord"):
            assert manager.apply_theme(theme_id)
            bg = tokens.qcolor(tokens.Colors.BG)
            expected = (
                f"rgba({bg.red()}, {bg.green()}, {bg.blue()}, "
                f"{tokens.WINDOW_OPACITY})"
            )
            assert expected in tokens.DARK_STYLESHEET
    finally:
        manager.apply_theme("dark")


def test_svg_icon_default_tint_tracks_theme(monkeypatch):
    from neoarch.frontend.mixins import icons as icons_module

    calls = []

    class _FakeIcon:
        def isNull(self):
            return True

    def fake_render_icon(path, size, tint):
        calls.append(tint)
        return _FakeIcon()

    monkeypatch.setattr(icons_module, "render_icon", fake_render_icon)
    obj = object.__new__(icons_module._IconsMixin)
    obj._icon_cache = {}

    manager = ThemeManager()
    monkeypatch.setattr(manager, "_save", lambda: None)
    try:
        for theme_id in ("dark", "light", "dracula", "nord"):
            assert manager.apply_theme(theme_id)
            expected = (
                tokens.Colors.WHITE
                if THEMES[theme_id]["is_dark"]
                else tokens.Colors.TEXT_2
            )
            assert tokens.icon_tint() == expected
            obj.get_svg_icon("/tmp/icon.svg", 18)
            assert calls[-1] == expected
    finally:
        manager.apply_theme("dark")
