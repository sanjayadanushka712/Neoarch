import os
import re
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from neoarch.frontend.icon_registry import (
    ICON_PATHS,
    brand_icon_candidates,
    brand_icon_path,
    brand_logo_path,
    icon_path,
    render_icon,
    render_pixmap,
    set_brand_assets,
    set_brand_pro,
    source_icon_path,
    status_icon_path,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_registered_icons_exist():
    missing = [name for name in ICON_PATHS if not os.path.isfile(icon_path(name))]
    assert missing == []


def test_relative_paths_and_unknown_names_fall_through():
    assert icon_path("ui/search.svg") == icon_path("ui/search")
    assert icon_path("does-not-exist.svg").endswith("does-not-exist.svg")


def test_bundle_nav_icon_alias_resolves():
    assert icon_path("local-builds") == icon_path("local_builds")
    assert os.path.isfile(icon_path("local-builds"))


def test_source_icons_have_safe_fallback():
    assert source_icon_path("AUR") == icon_path("sources/aur")
    assert source_icon_path("unknown") == icon_path("sources/packagename")


def test_status_and_brand_helpers():
    assert status_icon_path("high") == icon_path("status/high")
    assert brand_icon_path() in brand_icon_candidates()
    assert os.path.isfile(brand_icon_path())


def test_pro_brand_icon_uses_themed_artwork():
    try:
        set_brand_pro(False)
        assert Path(brand_icon_path()).name == "icon.png"
        set_brand_pro(True)
        assert Path(brand_icon_path()).name == "icon-pro.png"
        assert Path(brand_logo_path()).name == "logo-pro.png"
    finally:
        set_brand_pro(False)


def test_themed_brand_assets_can_be_selected_per_theme():
    try:
        set_brand_assets("app/icon-pro-evergreen", "app/logo-pro-evergreen")
        assert Path(brand_icon_path()).name == "icon-pro-evergreen.png"
        assert Path(brand_logo_path()).name == "logo-pro-evergreen.png"
    finally:
        set_brand_assets()


def test_render_svg_and_png(qapp):
    assert not render_pixmap("discover", 24, "#FFFFFF").isNull()
    assert not render_pixmap("app/icon", 24).isNull()
    assert not render_icon("discover", 24, "#FFFFFF").isNull()


def test_frontend_does_not_render_svgs_directly():
    frontend = Path(__file__).resolve().parents[2] / "neoarch" / "frontend"
    offenders = []
    for path in frontend.rglob("*.py"):
        if path.name == "icon_registry.py":
            continue
        if re.search(r"\bQSvgRenderer\b", path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(frontend)))
    assert offenders == []


def test_logical_icon_constants_are_registered():
    frontend = Path(__file__).resolve().parents[2] / "neoarch" / "frontend"
    pattern = re.compile(r'^_ICON_[A-Z0-9_]+\s*=\s*"([^"]+)"', re.MULTILINE)
    missing = []
    for path in frontend.rglob("*.py"):
        for name in pattern.findall(path.read_text(encoding="utf-8")):
            if name not in ICON_PATHS:
                missing.append(f"{path.relative_to(frontend)}: {name}")
    assert missing == []
