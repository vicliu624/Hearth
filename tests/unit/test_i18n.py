from __future__ import annotations

from hearth.web.i18n import TRANSLATIONS, translate


def test_translate_falls_back_when_localized_text_is_corrupted() -> None:
    assert translate("zh-CN", "nav.profile") == "账号信息"
    assert translate("zh-CN", "page.plugins") == "插件管理"
    assert translate("es", "bridges.not_found") == "The requested bridge was not found."
    assert "?" not in translate("zh-CN", "nav.profile")
    assert translate("en", "nav.profile") == "Profile"


def test_reviewed_chinese_and_english_catalogs_are_complete():
    from string import Formatter

    chinese, english = TRANSLATIONS["zh-CN"], TRANSLATIONS["en"]
    assert chinese.keys() == english.keys()
    assert len(chinese) >= 800
    fields = lambda value: {name for _, name, _, _ in Formatter().parse(value) if name}
    for key in chinese:
        assert chinese[key].strip(), key
        assert "??" not in chinese[key] and "\ufffd" not in chinese[key], key
        assert fields(chinese[key]) == fields(english[key]), key


def test_templates_and_frontend_reference_existing_catalog_keys():
    from pathlib import Path
    import re

    root = Path(__file__).resolve().parents[2]
    paths = list((root / "src/hearth/web/templates").glob("*.html")) + list(
        (root / "frontend/src").glob("*.tsx")
    )
    for path in paths:
        for key in re.findall(
            r"\bt\([\"\x27]([a-z0-9_.]+)[\"\x27]\s*[,)]",
            path.read_text(encoding="utf-8-sig"),
        ):
            if key.endswith("."):
                continue
            assert key in TRANSLATIONS["en"] and key in TRANSLATIONS["zh-CN"], (
                path.name,
                key,
            )


def test_operational_terms_preserve_meaning():
    assert translate("zh-CN", "nav.announces") == "通告"
    assert translate("zh-CN", "nav.routes") == "路径"
    assert translate("zh-CN", "field.last_seen") == "最近观测时间"
    assert "尚未应用" in translate("zh-CN", "notice.config_saved")
    assert "draft" in translate("en", "notice.config_saved")
    assert translate("zh-CN", "count.nodes", count=3) == "3 个节点"
    assert translate("en", "count.nodes", count=3) == "3 nodes"


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
