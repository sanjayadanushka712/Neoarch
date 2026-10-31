"""Sponsor roll in the About → Community tab.

The first sponsor is honoured explicitly (role "First Sponsor"), so the
ordering of `_SPONSORS` is part of the contract, not an implementation
detail. The copy is resolved through the i18n layer, so every bundled
catalog must carry the sponsor strings.
"""

import os

import pytest

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QScrollArea

from neoarch.backend.services import i18n
from neoarch.frontend.components import about_tab
from neoarch.resources.paths import ASSETS_DIR


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sponsors_list_is_not_empty():
    assert about_tab._SPONSORS, "at least one sponsor must be listed"


def test_first_sponsor_is_ferreol():
    first = about_tab._SPONSORS[0]
    assert first["name"] == "Ferreol"
    assert first["handle"] == "ferreol-fr"
    assert first["url"] == "https://github.com/ferreol-fr"


def test_every_sponsor_has_the_fields_the_card_needs():
    for sponsor in about_tab._SPONSORS:
        assert sponsor["name"].strip()
        assert sponsor["handle"].strip()
        assert sponsor["url"].startswith("https://")
        assert sponsor["copy"]


def test_sponsor_portrait_is_on_disk():
    """The card shows a portrait, never an empty badge."""
    for sponsor in about_tab._SPONSORS:
        avatar = sponsor.get("avatar")
        assert avatar, "a sponsor needs a portrait file"
        path = os.path.join(str(ASSETS_DIR), "icons", "app", avatar)
        assert os.path.exists(path), f"missing portrait: {path}"


def test_sponsor_copy_marks_the_first_sponsor():
    first = about_tab._SPONSORS[0]
    copy = about_tab._sponsor_copy(first["copy"])
    assert copy["role"] == "First Sponsor"
    assert copy["link"] == "\u2197 GitHub"
    assert copy["note"].strip()
    assert "NeoArch" in copy["note"]


def test_unknown_sponsor_key_falls_back_to_plain_sponsor():
    copy = about_tab._sponsor_copy("nobody")
    assert copy["role"] == "Sponsor"
    assert copy["note"] == ""


@pytest.mark.parametrize("lang", sorted(i18n.available_languages()))
def test_bundled_catalogs_translate_the_sponsor_strings(lang):
    cat = i18n.load_catalog(lang)
    assert cat.get("Sponsors")
    assert cat.get("First Sponsor")
    assert cat.get("Sponsor")
    assert cat.get("Sponsor message")
    note = [k for k in cat if k.startswith("His early backing")]
    assert note, f"{lang} catalog is missing the sponsor note"


def test_community_tab_renders_the_sponsor_row(qapp):
    tab = about_tab._CommunityTab()
    labels = [lbl.text() for lbl in tab.findChildren(QLabel)]
    first = about_tab._SPONSORS[0]
    assert "Sponsors" in labels
    assert first["name"] in labels
    assert f"@{first['handle']}" in labels
    assert any(text.startswith("★ First Sponsor") for text in labels)
    assert any(text.startswith("His early backing") for text in labels)


def test_community_tab_links_to_the_sponsor_profile(qapp, monkeypatch):
    opened = []
    monkeypatch.setattr(about_tab, "_open_url",
                        lambda url: opened.append(url))
    tab = about_tab._CommunityTab()
    btn = tab.findChild(QPushButton, "sponsorLink")
    assert btn is not None
    assert btn.text() == "\u2197 GitHub"
    btn.click()
    assert opened == ["https://github.com/ferreol-fr"]


def test_community_tab_fits_without_a_scrollbar(qapp):
    """The page must fit the smallest window the app allows.

    A scrollbar squeezed the cards against the viewport edge and clipped
    their rounded corners — the two-column layout keeps everything on
    screen instead.
    """
    tab = about_tab._CommunityTab()
    tab.resize(966, 689)   # About content area inside a 1280x850 window
    tab.show()
    qapp.processEvents()
    scroll = tab.findChild(QScrollArea)
    assert scroll is not None
    assert not scroll.verticalScrollBar().isVisible()


def test_community_tab_uses_two_columns(qapp):
    """People on the left, support on the right — never a single column."""
    tab = about_tab._CommunityTab()
    tab.resize(966, 689)
    tab.show()
    qapp.processEvents()
    cards = [f for f in tab.findChildren(QFrame)
             if f.objectName() == "settingsCard"]
    assert len(cards) >= 4
    columns = {f.mapToGlobal(QPoint(0, 0)).x() for f in cards}
    assert len(columns) == 2, "cards should be split across two columns"
