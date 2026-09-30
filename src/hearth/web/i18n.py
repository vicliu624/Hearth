from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Request

DEFAULT_LOCALE = "zh-CN"
LANG_COOKIE_NAME = "hearth_lang"
SUPPORTED_LOCALES = {
    "zh-CN": "简体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
}
LOCALE_ALIASES = {
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-hans": "zh-CN",
    "en-us": "en",
    "en-gb": "en",
    "ja-jp": "ja",
    "ko-kr": "ko",
    "es-es": "es",
    "es-mx": "es",
}
LOCALE_DIR = Path(__file__).with_name("locales")
TRANSLATIONS: dict[str, dict[str, str]] = {
    locale: json.loads((LOCALE_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    for locale in SUPPORTED_LOCALES
}


def normalize_locale(value: str | None) -> str:
    if not value or not value.strip():
        return DEFAULT_LOCALE
    candidate = value.strip().lower()
    if candidate in LOCALE_ALIASES:
        return LOCALE_ALIASES[candidate]
    for locale in SUPPORTED_LOCALES:
        if locale.lower() == candidate or locale.split("-")[0].lower() == candidate:
            return locale
    return DEFAULT_LOCALE


def resolve_locale(request: Request) -> str:
    requested = request.query_params.get("lang") or request.cookies.get(
        LANG_COOKIE_NAME
    )
    if requested:
        return normalize_locale(requested)
    preferences = []
    for raw in request.headers.get("accept-language", "").split(","):
        parts = raw.strip().split(";")
        language = parts[0].lower()
        try:
            quality = float(parts[1].split("=", 1)[1]) if len(parts) > 1 else 1.0
        except (ValueError, IndexError):
            continue
        if quality > 0 and (
            language in LOCALE_ALIASES
            or language in {code.lower() for code in SUPPORTED_LOCALES}
        ):
            preferences.append((quality, language))
    return (
        normalize_locale(max(preferences, key=lambda item: item[0])[1])
        if preferences
        else DEFAULT_LOCALE
    )


def _translation_looks_corrupted(value: object, locale: str | None = None) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if "\ufffd" in value or "??" in value:
        return True
    if "?" not in value:
        return False
    if not value.replace("?", "").strip():
        return True
    return not (value.rstrip().endswith("?") and value.count("?") == 1)


def translate(locale: str, key: str, **kwargs: object) -> str:
    table = TRANSLATIONS.get(locale, TRANSLATIONS[DEFAULT_LOCALE])
    english = TRANSLATIONS["en"].get(key)
    default = TRANSLATIONS[DEFAULT_LOCALE].get(key)
    template = table.get(key) or english or default or key
    if locale != "en" and _translation_looks_corrupted(template, locale):
        template = english or default or key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template


def translate_diagnostic(locale: str, message: str) -> str:
    key = "diagnostic." + re.sub(r"\W+", "_", message.lower()).strip("_")
    return translate(locale, key) if key in TRANSLATIONS["en"] else message


def build_locale_options(
    current_locale: str, request: Request
) -> list[dict[str, object]]:
    base_query = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key != "lang"
    ]
    return [
        {
            "code": code,
            "label": label,
            "href": request.url.path + "?" + urlencode([*base_query, ("lang", code)]),
            "active": code == current_locale,
        }
        for code, label in SUPPORTED_LOCALES.items()
    ]
