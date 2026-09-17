#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Массовая обработка DOI:
1. получает название статьи, журнал, год, PMID/PMCID;
2. ищет легально доступный PDF в Europe PMC;
3. затем ищет OA-копию через Unpaywall;
4. сохраняет PDF, metadata.csv и unresolved.csv.

Запуск:
    python download_articles.py

Можно также передать TXT-файл с DOI:
    python download_articles.py "my_text.txt"
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

EMAIL = "arina.atom@gmail.com"
OUTPUT_DIR = Path("TMT_articles")
PDF_DIR = OUTPUT_DIR / "PDF"
TIMEOUT = 30
PDF_TIMEOUT = 20
SLEEP_SECONDS = 0.2

DEFAULT_DOIS = [
    "10.1021/acs.jproteome.2c00838",
    "10.1021/ac0262560",
    "10.1021/ac702422x",
    "10.1021/ac301572t",
    "10.1021/ac500140s",
    "10.1038/s41592-020-0781-4",
    "10.1021/acs.jproteome.1c00168",
    "10.1002/cbic.201800650",
    "10.1038/s41596-018-0006-9",
    "10.1093/nar/gkac1040",
    "10.1093/nar/gkae1011",
    "10.1038/s41592-020-0955-0",
    "10.1093/nar/gkab1081",
    "10.1158/2767-9764.CRC-24-0243",
    "10.1158/2159-8290.CD-13-0219",
    "10.1038/nature13438",
    "10.1038/nature18003",
    "10.1016/j.cell.2020.10.036",
    "10.1016/j.cell.2019.10.007",
    "10.1016/j.cell.2019.03.030",
    "10.1016/j.cell.2020.01.026",
    "10.1016/j.cell.2020.06.013",
    "10.1016/j.cell.2021.07.016",
    "10.1016/j.ccell.2020.12.007",
    "10.1016/j.ccell.2021.01.006",
    "10.1016/j.cell.2021.08.023",
    "10.1016/j.ccell.2023.06.009",
    "10.1021/pr501254j",
    "10.1016/j.cell.2018.03.022",
    "10.1016/j.cell.2020.08.036",
    "10.1126/science.aaz1776",
    "10.1016/j.cell.2019.12.023",
    "10.1038/s41586-019-1186-3",
    "10.1002/mas.21860",
    "10.3390/proteomes14020016",
    "10.1038/s41597-021-00890-2",
    "10.1371/journal.pcbi.1011828",
    "10.1021/acs.jproteome.4c00788",
]

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.I)


def unique_preserve_order(items):
    seen = set()
    result = []
    for item in items:
        item = item.strip().rstrip(").,;:]}'\"")
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def extract_dois(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    return unique_preserve_order(DOI_RE.findall(text))


def request_bytes(url, accept="application/json", timeout=None):
    headers = {
        "User-Agent": f"TMT-article-downloader/1.0 (mailto:{EMAIL})",
        "Accept": accept,
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout or TIMEOUT) as response:
        return response.read(), response.headers, response.geturl()


def get_json(url):
    data, _, _ = request_bytes(url, "application/json")
    return json.loads(data.decode("utf-8"))


def safe_filename(value, max_len=150):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" ._")
    return (value[:max_len] or "article").strip()


def crossref_metadata(doi):
    encoded = quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded}?mailto={quote(EMAIL)}"
    try:
        message = get_json(url).get("message", {})
    except Exception as exc:
        return {}, f"Crossref: {exc}"

    title_list = message.get("title") or []
    container = message.get("container-title") or []
    authors = []
    for author in message.get("author") or []:
        name = " ".join(
            part for part in [author.get("given", ""), author.get("family", "")]
            if part
        )
        if name:
            authors.append(name)

    year = ""
    for field in ("published-print", "published-online", "issued", "created"):
        parts = (message.get(field) or {}).get("date-parts") or []
        if parts and parts[0]:
            year = parts[0][0]
            break

    article_number = (
        message.get("article-number")
        or message.get("page")
        or message.get("publisher-location")
        or ""
    )

    links = []
    for item in message.get("link") or []:
        if item.get("URL"):
            links.append({
                "url": item.get("URL"),
                "content_type": item.get("content-type", ""),
                "intended_application": item.get("intended-application", ""),
            })

    return {
        "title": title_list[0] if title_list else "",
        "journal": container[0] if container else "",
        "year": year,
        "authors": "; ".join(authors),
        "article_number": article_number,
        "publisher": message.get("publisher", ""),
        "crossref_url": message.get("URL", f"https://doi.org/{doi}"),
        "crossref_links": links,
    }, ""


def europe_pmc_metadata(doi):
    params = urlencode({
        "query": f'DOI:"{doi}"',
        "format": "json",
        "pageSize": 5,
        "resultType": "core",
    })
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + params
    try:
        payload = get_json(url)
    except Exception as exc:
        return {}, f"Europe PMC: {exc}"

    results = payload.get("resultList", {}).get("result", [])
    if not results:
        return {}, ""

    exact = None
    for result in results:
        if str(result.get("doi", "")).lower() == doi.lower():
            exact = result
            break
    result = exact or results[0]

    return {
        "title": result.get("title", ""),
        "journal": result.get("journalTitle", ""),
        "year": result.get("pubYear", ""),
        "pmid": result.get("pmid", ""),
        "pmcid": result.get("pmcid", ""),
        "is_open_access": result.get("isOpenAccess", ""),
        "author_string": result.get("authorString", ""),
        "europe_pmc_url": (
            f"https://europepmc.org/article/MED/{result.get('pmid')}"
            if result.get("pmid")
            else ""
        ),
    }, ""


def unpaywall_metadata(doi):
    encoded = quote(doi, safe="")
    url = f"https://api.unpaywall.org/v2/{encoded}?email={quote(EMAIL)}"
    try:
        payload = get_json(url)
    except Exception as exc:
        return {}, f"Unpaywall: {exc}"

    best = payload.get("best_oa_location") or {}
    return {
        "is_oa": payload.get("is_oa", False),
        "oa_status": payload.get("oa_status", ""),
        "pdf_url": best.get("url_for_pdf") or "",
        "landing_url": best.get("url") or "",
        "license": best.get("license") or "",
        "host_type": best.get("host_type") or "",
    }, ""


def semantic_scholar_pdf(doi):
    encoded = quote(doi, safe="")
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{encoded}?fields=openAccessPdf,externalIds,title"
    try:
        payload = get_json(url)
    except Exception as exc:
        return "", f"Semantic Scholar: {exc}"
    oa = payload.get("openAccessPdf") or {}
    return oa.get("url", ""), ""


def openalex_pdf(doi):
    encoded = quote(doi, safe="")
    url = f"https://api.openalex.org/works/https://doi.org/{encoded}"
    try:
        payload = get_json(url)
    except Exception as exc:
        return "", f"OpenAlex: {exc}"
    for location in payload.get("open_access", {}).get("oa_locations", []):
        pdf_url = location.get("pdf_url") or ""
        if pdf_url:
            return pdf_url, ""
    for location in payload.get("locations", []):
        pdf_url = location.get("pdf_url") or ""
        if pdf_url:
            return pdf_url, ""
    return "", ""


def europe_pmc_fulltext_links(pmcid):
    if not pmcid:
        return []
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextLinks"
    try:
        payload = get_json(url)
    except Exception:
        return []
    links = []
    for item in payload.get("fullTextLinkList", {}).get("fullTextLink", []):
        if item.get("availability") == "Open access" and item.get("url"):
            links.append(item["url"])
    return links


def is_valid_pdf(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size > 1000 and path.read_bytes()[:4] == b"%PDF"
    except OSError:
        return False


def download_pdf(url, destination):
    if not url:
        return False, "empty URL"

    try:
        data, headers, final_url = request_bytes(
            url,
            "application/pdf,application/octet-stream;q=0.9,*/*;q=0.1",
            timeout=PDF_TIMEOUT,
        )
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return False, str(exc)
    except Exception as exc:
        return False, str(exc)

    content_type = headers.get("Content-Type", "").lower()
    if not data.startswith(b"%PDF"):
        return False, f"not PDF; content-type={content_type}; final={final_url}"

    destination.write_bytes(data)
    return True, final_url


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    PDF_DIR.mkdir(exist_ok=True)

    if len(sys.argv) > 1:
        source = Path(sys.argv[1])
        if not source.exists():
            raise SystemExit(f"Файл не найден: {source}")
        dois = extract_dois(source)
    else:
        dois = DEFAULT_DOIS

    if not dois:
        raise SystemExit("DOI не найдены.")

    print(f"Найдено DOI: {len(dois)}")
    metadata_rows = []
    unresolved_rows = []
    downloaded = 0

    for index, doi in enumerate(dois, 1):
        print(f"[{index}/{len(dois)}] {doi}", flush=True)

        crossref, crossref_error = crossref_metadata(doi)
        time.sleep(SLEEP_SECONDS)
        epmc, epmc_error = europe_pmc_metadata(doi)
        time.sleep(SLEEP_SECONDS)

        title = epmc.get("title") or crossref.get("title") or doi
        journal = epmc.get("journal") or crossref.get("journal") or ""
        year = epmc.get("year") or crossref.get("year") or ""
        pmid = epmc.get("pmid", "")
        pmcid = epmc.get("pmcid", "")

        pdf_status = "not downloaded"
        pdf_source = ""
        pdf_url = ""
        errors = [x for x in [crossref_error, epmc_error] if x]

        filename = safe_filename(f"{index:02d}_{year}_{title}") + ".pdf"
        destination = PDF_DIR / filename

        if is_valid_pdf(destination):
            downloaded += 1
            metadata_rows.append({
                "№": index,
                "DOI": doi,
                "Title": title,
                "Journal": journal,
                "Year": year,
                "Article number/pages": crossref.get("article_number", ""),
                "PMID": pmid,
                "PMCID": pmcid,
                "DOI link": f"https://doi.org/{doi}",
                "Europe PMC": epmc.get("europe_pmc_url", ""),
                "Open access": "",
                "OA status": "",
                "PDF status": "downloaded",
                "PDF source": "already present",
                "PDF URL": "",
                "Local PDF": str(destination),
                "Errors": "",
            })
            print(f"  -> already downloaded", flush=True)
            continue

        # 1. Europe PMC direct PDF
        if pmcid:
            epmc_pdf = f"https://europepmc.org/articles/{pmcid}?pdf=render"
            ok, detail = download_pdf(epmc_pdf, destination)
            if ok:
                pdf_status = "downloaded"
                pdf_source = "Europe PMC"
                pdf_url = detail
            else:
                errors.append("Europe PMC PDF: " + detail)

        # 2. Unpaywall
        unpaywall = {}
        unpaywall_error = ""
        if pdf_status != "downloaded":
            unpaywall, unpaywall_error = unpaywall_metadata(doi)
            time.sleep(SLEEP_SECONDS)
            if unpaywall_error:
                errors.append(unpaywall_error)

            candidates = [
                unpaywall.get("pdf_url", ""),
                unpaywall.get("landing_url", ""),
            ]
            for candidate in unique_preserve_order(candidates):
                ok, detail = download_pdf(candidate, destination)
                if ok:
                    pdf_status = "downloaded"
                    pdf_source = "Unpaywall"
                    pdf_url = detail
                    break
                if candidate:
                    errors.append("Unpaywall candidate: " + detail)

        # 3. Europe PMC full-text links
        if pdf_status != "downloaded":
            for candidate in europe_pmc_fulltext_links(pmcid):
                ok, detail = download_pdf(candidate, destination)
                if ok:
                    pdf_status = "downloaded"
                    pdf_source = "Europe PMC full-text link"
                    pdf_url = detail
                    break
                errors.append("Europe PMC full-text: " + detail)

        # 4. Semantic Scholar
        if pdf_status != "downloaded":
            ss_pdf, ss_error = semantic_scholar_pdf(doi)
            time.sleep(SLEEP_SECONDS)
            if ss_error:
                errors.append(ss_error)
            if ss_pdf:
                ok, detail = download_pdf(ss_pdf, destination)
                if ok:
                    pdf_status = "downloaded"
                    pdf_source = "Semantic Scholar"
                    pdf_url = detail
                else:
                    errors.append("Semantic Scholar PDF: " + detail)

        # 5. OpenAlex
        if pdf_status != "downloaded":
            oa_pdf, oa_error = openalex_pdf(doi)
            time.sleep(SLEEP_SECONDS)
            if oa_error:
                errors.append(oa_error)
            if oa_pdf:
                ok, detail = download_pdf(oa_pdf, destination)
                if ok:
                    pdf_status = "downloaded"
                    pdf_source = "OpenAlex"
                    pdf_url = detail
                else:
                    errors.append("OpenAlex PDF: " + detail)

        # 6. Crossref links that explicitly claim PDF
        if pdf_status != "downloaded":
            for link in crossref.get("crossref_links", []):
                if "pdf" not in str(link.get("content_type", "")).lower():
                    continue
                candidate = link.get("url", "")
                ok, detail = download_pdf(candidate, destination)
                if ok:
                    pdf_status = "downloaded"
                    pdf_source = "Crossref publisher link"
                    pdf_url = detail
                    break
                errors.append("Crossref PDF candidate: " + detail)

        if pdf_status == "downloaded":
            print(f"  -> downloaded via {pdf_source}", flush=True)
            downloaded += 1
        else:
            print(f"  -> NOT downloaded", flush=True)
            unresolved_rows.append({
                "№": index,
                "DOI": doi,
                "Title": title,
                "DOI link": f"https://doi.org/{doi}",
                "Europe PMC": epmc.get("europe_pmc_url", ""),
                "Unpaywall landing": unpaywall.get("landing_url", ""),
                "Reason": " | ".join(errors),
            })

        metadata_rows.append({
            "№": index,
            "DOI": doi,
            "Title": title,
            "Journal": journal,
            "Year": year,
            "Article number/pages": crossref.get("article_number", ""),
            "PMID": pmid,
            "PMCID": pmcid,
            "DOI link": f"https://doi.org/{doi}",
            "Europe PMC": epmc.get("europe_pmc_url", ""),
            "Open access": unpaywall.get("is_oa", epmc.get("is_open_access", "")),
            "OA status": unpaywall.get("oa_status", ""),
            "PDF status": pdf_status,
            "PDF source": pdf_source,
            "PDF URL": pdf_url,
            "Local PDF": str(destination) if pdf_status == "downloaded" else "",
            "Errors": " | ".join(errors),
        })

    metadata_file = OUTPUT_DIR / "metadata.csv"
    with metadata_file.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(metadata_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metadata_rows)

    unresolved_file = OUTPUT_DIR / "unresolved.csv"
    if unresolved_rows:
        with unresolved_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(unresolved_rows[0].keys()))
            writer.writeheader()
            writer.writerows(unresolved_rows)
    else:
        unresolved_file.write_text(
            "Все статьи скачаны или найдены.\n", encoding="utf-8-sig"
        )

    print()
    print(f"Готово. Скачано PDF: {downloaded}/{len(dois)}")
    print(f"Папка: {OUTPUT_DIR.resolve()}")
    print(f"Метаданные: {metadata_file.resolve()}")
    print(f"Не скачано: {unresolved_file.resolve()}")
    print("Важно: скрипт скачивает только файлы, доступные без авторизации.")


if __name__ == "__main__":
    main()
