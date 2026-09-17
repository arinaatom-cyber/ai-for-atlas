"""Load RU/EN strings from site_assets/i18n.js for static HTML fallbacks."""

from __future__ import annotations



import html

import re

from functools import lru_cache

from pathlib import Path



_JS = Path(__file__).resolve().parent / "site_assets" / "i18n.js"





def _unescape(s: str) -> str:

    return s.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")





@lru_cache(maxsize=1)

def load_i18n_dicts() -> tuple[dict[str, str], dict[str, str]]:

    js = _JS.read_text(encoding="utf-8")

    ru: dict[str, str] = {}

    en: dict[str, str] = {}



    m = re.search(r'brand_title:\s*"([^"]+)"', js)

    if m:

        ru["brand_title"] = en["brand_title"] = m.group(1)



    for m in re.finditer(

        r"(\w+):\s*\{\s*ru:\s*\"((?:[^\"\\]|\\.)*)\"\s*,\s*en:\s*\"((?:[^\"\\]|\\.)*)\"\s*,?\s*\}",

        js,

        re.S,

    ):

        ru[m.group(1)] = _unescape(m.group(2))

        en[m.group(1)] = _unescape(m.group(3))



    for lang, target in (("ru", ru), ("en", en)):

        block = re.search(rf"{lang}:\s*\{{(.*?)\n\s*\}},?\s*\n\s*(?:en:|}}\);)", js, re.S)

        if not block:

            continue

        body = block.group(1)

        for km in re.finditer(

            r"(\w+):\s*(?:\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)'|(\[[^\]]*\]))",

            body,

        ):

            key = km.group(1)

            val = km.group(2) or km.group(3) or km.group(4) or ""

            if val.startswith("["):

                continue

            target[key] = _unescape(val)

        for km in re.finditer(r"(\w+):\s*\n\s*\"((?:[^\"\\]|\\.)*)\"", body):

            target[km.group(1)] = _unescape(km.group(2))



    return ru, en





def t(key: str, lang: str = "ru") -> str:

    ru, en = load_i18n_dicts()

    d = ru if lang == "ru" else en

    return d.get(key) or en.get(key) or ru.get(key) or key





def ru(key: str) -> str:

    return t(key, "ru")





def en(key: str) -> str:

    return t(key, "en")





def ru_project_count(n: int) -> str:

    n = abs(int(n))

    if n % 10 == 1 and n % 100 != 11:

        return f"{n} новый проект"

    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):

        return f"{n} новых проекта"

    return f"{n} новых проектов"





def en_project_count(n: int) -> str:

    n = abs(int(n))

    return f"{n} new project" if n == 1 else f"{n} new projects"





def ru_row_count(n: int) -> str:

    n = abs(int(n))

    if n % 10 == 1 and n % 100 != 11:

        return f"{n} запись"

    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):

        return f"{n} записи"

    return f"{n} записей"





def en_row_count(n: int) -> str:

    n = abs(int(n))

    return f"{n} row" if n == 1 else f"{n} rows"





def hydrate_i18n_html(path: Path, *, lang: str = "ru") -> None:

    """Fill empty data-i18n / placeholder nodes with fallback text."""

    text = path.read_text(encoding="utf-8")

    ru_d, en_d = load_i18n_dicts()

    d = ru_d if lang == "ru" else en_d



    def fill_suffix(m: re.Match[str]) -> str:
        key = m.group(1)
        attrs = m.group(2) or ""
        suffix_m = re.search(r'data-i18n-suffix="([^"]*)"', attrs)
        if not suffix_m or key not in d:
            return m.group(0)
        suffix = suffix_m.group(1)
        val = html.escape(d[key].replace("{n}", suffix).replace("{score}", suffix))
        return f'data-i18n="{key}"{attrs}>{val}</'

    text = re.sub(
        r'data-i18n="([^"]+)"([^>]*data-i18n-suffix="[^"]*"[^>]*?)>\s*</',
        fill_suffix,
        text,
    )

    def fill_tag(m: re.Match[str]) -> str:
        key = m.group(1)
        attrs = m.group(2) or ""
        if "data-i18n-suffix=" in attrs or key not in d:
            return m.group(0)
        val = html.escape(d[key])
        return f'data-i18n="{key}"{attrs}>{val}</'

    text = re.sub(
        r'data-i18n="([^"]+)"([^>]*?)>\s*</',
        fill_tag,
        text,
    )



    def fill_ph(m: re.Match[str]) -> str:

        key = m.group(1)

        if key not in d:

            return m.group(0)

        return f'data-i18n-placeholder="{key}" placeholder="{html.escape(d[key], quote=True)}"'



    text = re.sub(

        r'data-i18n-placeholder="([^"]+)"(?!\s+placeholder=)',

        fill_ph,

        text,

    )



    def fill_title(m: re.Match[str]) -> str:

        key = m.group(1)

        ws = m.group(2) or ""

        if key not in d:

            return m.group(0)

        return (
            f'data-i18n-title="{key}" title="{html.escape(d[key], quote=True)}"{ws}>'
        )



    text = re.sub(

        r'data-i18n-title="([^"]+)"(?!\s+title=)(\s*)>',

        fill_title,

        text,

    )



    path.write_text(text, encoding="utf-8")





def hydrate_site_html(root: Path, *, lang: str = "ru") -> int:

    """Hydrate all HTML under root (skip tiny redirect stubs)."""

    n = 0

    for hp in sorted(root.rglob("*.html")):

        if hp.stat().st_size < 600 and "refresh" in hp.read_text(encoding="utf-8", errors="replace")[:800]:

            continue

        hydrate_i18n_html(hp, lang=lang)

        n += 1

    return n

