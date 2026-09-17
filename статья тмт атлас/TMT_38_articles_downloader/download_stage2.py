#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Second-stage downloader using curl_cffi and extended OA sources."""

from __future__ import annotations

import csv
import json
import re
import tarfile
import time
import unicodedata
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urljoin

from curl_cffi import requests

EMAIL = "arina.atom@gmail.com"
BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "TMT_articles"
PDF_DIR = OUTPUT / "PDF"
METADATA = OUTPUT / "metadata.csv"
UNRESOLVED = OUTPUT / "unresolved.csv"
TIMEOUT = 45
SLEEP = 0.25

SESSION = requests.Session(impersonate="chrome120")


def safe_filename(value: str, max_len: int = 150) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" ._")
    return (value[:max_len] or "article").strip()


def is_valid_pdf(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size > 1000 and path.read_bytes()[:4] == b"%PDF"
    except OSError:
        return False


def save_pdf(data: bytes, destination: Path) -> bool:
    if not data.startswith(b"%PDF"):
        return False
    destination.write_bytes(data)
    return True


def fetch(url: str, referer: str = "") -> tuple[bytes, str, str]:
    headers = {}
    if referer:
        headers["Referer"] = referer
    response = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True, headers=headers)
    content_type = response.headers.get("content-type", "")
    return response.content, content_type, str(response.url)


def unpaywall_all(doi: str) -> list[str]:
    url = f"https://api.unpaywall.org/v2/{quote(doi, safe='')}?email={quote(EMAIL)}"
    try:
        payload = SESSION.get(url, timeout=TIMEOUT).json()
    except Exception:
        return []
    urls = []
    for location in payload.get("oa_locations", []):
        for key in ("url_for_pdf", "url"):
            value = location.get(key) or ""
            if value:
                urls.append(value)
    best = payload.get("best_oa_location") or {}
    for key in ("url_for_pdf", "url"):
        value = best.get(key) or ""
        if value:
            urls.append(value)
    return unique(urls)


def openalex_all(doi: str) -> list[str]:
    url = f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='')}"
    try:
        payload = SESSION.get(url, timeout=TIMEOUT).json()
    except Exception:
        return []
    urls = []
    for location in payload.get("open_access", {}).get("oa_locations", []):
        if location.get("pdf_url"):
            urls.append(location["pdf_url"])
    for location in payload.get("locations", []):
        if location.get("pdf_url"):
            urls.append(location["pdf_url"])
    primary = payload.get("primary_location") or {}
    if primary.get("pdf_url"):
        urls.append(primary["pdf_url"])
    return unique(urls)


def europe_pmc_info(doi: str) -> dict:
    params = {
        "query": f'DOI:"{doi}"',
        "format": "json",
        "pageSize": 3,
        "resultType": "core",
    }
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    try:
        payload = SESSION.get(url, params=params, timeout=TIMEOUT).json()
    except Exception:
        return {}
    for result in payload.get("resultList", {}).get("result", []):
        if str(result.get("doi", "")).lower() == doi.lower():
            return result
    results = payload.get("resultList", {}).get("result", [])
    return results[0] if results else {}


def pmc_candidates(pmcid: str, doi: str) -> list[str]:
    pmcid = pmcid.strip()
    if not pmcid:
        return []
    if not pmcid.upper().startswith("PMC"):
        pmcid = "PMC" + pmcid
    suffix = doi.split("/")[-1]
    page = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    candidates = [
        f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/{suffix}.pdf",
        f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/main.pdf",
        f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/{suffix}.pdf",
        f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf",
    ]
    try:
        html = SESSION.get(page, timeout=TIMEOUT).text
        for match in re.findall(r'href="([^"]+\.pdf[^"]*)"', html, flags=re.I):
            candidates.append(urljoin(page, match))
        meta = re.search(r'name="citation_pdf_url"\s+content="([^"]+)"', html)
        if meta:
            candidates.append(meta.group(1))
    except Exception:
        pass
    return unique(candidates)


def publisher_specific(doi: str) -> list[str]:
    urls = []
    if doi.startswith("10.1371/"):
        urls.append(
            "https://journals.plos.org/ploscompbiol/article/file"
            f"?id={doi}&type=printable"
        )
        urls.append(
            f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable"
        )
    if doi.startswith("10.3390/"):
        parts = doi.split("/")[-1]
        journal_issue = parts.rsplit(".", 1)[0]
        article_no = parts.rsplit(".", 1)[-1]
        urls.append(f"https://www.mdpi.com/{journal_issue}/{article_no}/pdf")
    if doi.startswith("10.1093/nar/"):
        suffix = doi.split("/")[-1]
        urls.append(f"https://academic.oup.com/nar/article-pdf/doi/10.1093/nar/{suffix}/{suffix}.pdf")
    if doi.startswith("10.1038/"):
        urls.append(f"https://www.nature.com/articles/{doi.split('/',1)[1]}.pdf")
    return urls


def unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def try_download(candidates: list[str], destination: Path, referer: str = "") -> tuple[bool, str, str]:
    for url in candidates:
        try:
            data, content_type, final_url = fetch(url, referer=referer)
            if save_pdf(data, destination):
                return True, final_url, ""
            detail = f"not PDF from {final_url} ({content_type})"
        except Exception as exc:
            detail = f"{url}: {exc}"
        time.sleep(0.1)
    return False, "", detail if "detail" in locals() else "no candidates"


def load_rows() -> list[dict]:
    with METADATA.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    downloaded_now = 0
    still_missing = []

    print(f"Stage 2: retrying {len(rows)} articles", flush=True)

    for row in rows:
        index = int(row["№"])
        doi = row["DOI"]
        title = row["Title"]
        year = row.get("Year", "")
        pmcid = row.get("PMCID", "")
        local = row.get("Local PDF", "")

        if local and is_valid_pdf(Path(local)):
            print(f"[{index}] skip existing", flush=True)
            continue

        filename = safe_filename(f"{index:02d}_{year}_{title}") + ".pdf"
        destination = PDF_DIR / filename

        if is_valid_pdf(destination):
            print(f"[{index}] skip existing file", flush=True)
            continue

        print(f"[{index}] {doi}", flush=True)
        candidates = []
        candidates.extend(publisher_specific(doi))
        candidates.extend(pmc_candidates(pmcid, doi))
        candidates.extend(unpaywall_all(doi))
        time.sleep(SLEEP)
        candidates.extend(openalex_all(doi))
        time.sleep(SLEEP)

        epmc = europe_pmc_info(doi)
        if epmc.get("pmcid") and not pmcid:
            candidates.extend(pmc_candidates(epmc["pmcid"], doi))

        referer = f"https://doi.org/{doi}"
        ok, final_url, _ = try_download(unique(candidates), destination, referer=referer)
        if ok:
            downloaded_now += 1
            row["PDF status"] = "downloaded"
            row["PDF source"] = "stage2 curl_cffi"
            row["PDF URL"] = final_url
            row["Local PDF"] = str(destination)
            print(f"  -> OK {final_url}", flush=True)
        else:
            still_missing.append(row)
            print(f"  -> FAIL", flush=True)

    # refresh metadata
    with METADATA.open(encoding="utf-8-sig", newline="") as handle:
        fieldnames = rows[0].keys()
    with METADATA.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    missing_rows = [r for r in rows if r.get("PDF status") != "downloaded"]
    if missing_rows:
        with UNRESOLVED.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["№", "DOI", "Title", "DOI link", "Europe PMC", "PMCID", "Reason"],
            )
            writer.writeheader()
            for row in missing_rows:
                writer.writerow({
                    "№": row["№"],
                    "DOI": row["DOI"],
                    "Title": row["Title"],
                    "DOI link": row["DOI link"],
                    "Europe PMC": row.get("Europe PMC", ""),
                    "PMCID": row.get("PMCID", ""),
                    "Reason": "stage2 failed",
                })

    total = sum(1 for r in rows if r.get("PDF status") == "downloaded")
    print(f"\nStage 2 done. New downloads: {downloaded_now}", flush=True)
    print(f"Total downloaded: {total}/{len(rows)}", flush=True)
    print(f"Still missing: {len(missing_rows)}", flush=True)


if __name__ == "__main__":
    main()
