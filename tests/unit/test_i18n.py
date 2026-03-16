from __future__ import annotations

from hearth.web.i18n import TRANSLATIONS, translate


def test_translate_falls_back_when_localized_text_is_corrupted() -> None:
    assert translate("zh-CN", "nav.profile") == "Profile"
    assert translate("zh-CN", "page.plugins") == "Hearth Plugins"
    assert translate("es", "bridges.not_found") == "The requested bridge was not found."
    assert "?" not in translate("zh-CN", "nav.profile")
    assert translate("en", "nav.profile") == "Profile"


def test_translate_keeps_legitimate_spanish_question_marks() -> None:
    key = "test.legitimate.question"
    original_en = TRANSLATIONS["en"].get(key)
    original_es = TRANSLATIONS["es"].get(key)

    TRANSLATIONS["en"][key] = "English fallback"
    TRANSLATIONS["es"][key] = "¿Listo?"
    try:
        assert translate("es", key) == "¿Listo?"
    finally:
        if original_en is None:
            TRANSLATIONS["en"].pop(key, None)
        else:
            TRANSLATIONS["en"][key] = original_en

        if original_es is None:
            TRANSLATIONS["es"].pop(key, None)
        else:
            TRANSLATIONS["es"][key] = original_es
