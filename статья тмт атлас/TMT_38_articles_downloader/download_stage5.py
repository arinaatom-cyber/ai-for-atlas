#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 5: extended legal OA download attempts."""

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
from playwright.sync_api import sync_playwright

EMAIL = "arina.atom@gmail.com"
BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "TMT_articles"
PDF_DIR = OUTPUT / "PDF"
METADATA = OUTPUT / "metadata.csv"
MIN_SIZE = 200_000
SESSION = requests.Session(impersonate="chrome120")
HEADERS = {
    "Referer": "https://scholar.google.com/",
    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
}


def safe_filename(value: str, max_len: int = 150) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" ._")
    return (value[:max_len] or "article").strip()


def is_valid_pdf(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size >= MIN_SIZE and path.read_bytes()[:4] == b"%PDF"
    except OSError:
        return False


def save_pdf(data: bytes, dest: Path) -> bool:
    if data.startswith(b"%PDF") and len(data) >= MIN_SIZE and b"RecruitmentKit" not in data[:50000]:
        dest.write_bytes(data)
        return True
    return False


def unique(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        item = item.strip()
        if item and item not in seen and "supplementary" not in item.lower():
            seen.add(item)
            out.append(item)
    return out


def fetch_pdf(url: str) -> tuple[bytes, str]:
    r = SESSION.get(url, timeout=60, allow_redirects=True, headers=HEADERS)
    return r.content, str(r.url)


def unpaywall_urls(doi: str) -> list[str]:
    url = f"https://api.unpaywall.org/v2/{quote(doi, safe='')}?email={quote(EMAIL)}"
    try:
        data = SESSION.get(url, timeout=30).json()
    except Exception:
        return []
    urls = []
    for loc in data.get("oa_locations", []):
        for k in ("url_for_pdf", "url"):
            if loc.get(k):
                urls.append(loc[k])
    best = data.get("best_oa_location") or {}
    for k in ("url_for_pdf", "url"):
        if best.get(k):
            urls.append(best[k])
    return unique(urls)


def openalex_urls(doi: str) -> list[str]:
    url = f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='')}"
    try:
        data = SESSION.get(url, timeout=30).json()
    except Exception:
        return []
    urls = []
    for loc in data.get("open_access", {}).get("oa_locations", []):
        if loc.get("pdf_url"):
            urls.append(loc["pdf_url"])
        if loc.get("landing_page_url"):
            urls.append(loc["landing_page_url"])
    primary = data.get("primary_location") or {}
    if primary.get("pdf_url"):
        urls.append(primary["pdf_url"])
    return unique(urls)


def core_urls(doi: str) -> list[str]:
    url = f"https://api.core.ac.uk/v3/search/works?q=doi:{quote(doi, safe='')}"
    try:
        data = SESSION.get(url, timeout=30, headers={"Accept": "application/json"}).json()
    except Exception:
        return []
    urls = []
    for item in data.get("results", []):
        if item.get("downloadUrl"):
            urls.append(item["downloadUrl"])
        for link in item.get("links", []) or []:
            if link.get("type") == "download" and link.get("url"):
                urls.append(link["url"])
    return unique(urls)


def pmc_oa_package(pmcid: str) -> list[str]:
    if not pmcid:
        return []
    if not pmcid.upper().startswith("PMC"):
        pmcid = "PMC" + pmcid
    api = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
    try:
        root = ET.fromstring(SESSION.get(api, timeout=30).content)
    except Exception:
        return []
    urls = []
    for rec in root.findall("records/record"):
        for link in rec.findall("link"):
            href = link.get("href")
            if href:
                if href.startswith("ftp://"):
                    href = "https://ftp.ncbi.nlm.nih.gov" + href[23:]
                urls.append(href)
    return urls


def extract_pdf_from_tgz(url: str) -> bytes:
    data, _ = fetch_pdf(url)
    if not data.startswith(b"\x1f\x8b"):
        return b""
    tf = tarfile.open(fileobj=BytesIO(data), mode="r:gz")
    pdfs = [m for m in tf.getmembers() if m.name.lower().endswith(".pdf")]
    if not pdfs:
        return b""
    member = max(pdfs, key=lambda m: m.size)
    return tf.extractfile(member).read()


def publisher_urls(doi: str, pmcid: str = "") -> list[str]:
    urls = []
    suffix = doi.split("/")[-1]
    if doi.startswith("10.1371/"):
        urls += [
            f"https://journals.plos.org/ploscompbiol/article/file?id={doi}&type=printable",
            f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable",
            f"https://journals.plos.org/plosbiology/article/file?id={doi}&type=printable",
        ]
    if doi.startswith("10.3390/"):
        part = suffix.rsplit(".", 1)
        if len(part) == 2:
            urls.append(f"https://www.mdpi.com/{part[0]}/{part[1]}/pdf")
    if doi.startswith("10.1093/nar/"):
        urls += [
            f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf" if pmcid else "",
            f"https://academic.oup.com/nar/article-pdf/doi/10.1093/nar/{suffix}/{suffix}.pdf",
        ]
    if doi.startswith("10.1038/"):
        art = doi.split("/", 1)[1]
        urls.append(f"https://www.nature.com/articles/{art}.pdf")
    if doi.startswith("10.1002/"):
        urls.append(f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}")
    if doi.startswith("10.1158/"):
        urls.append(f"https://aacrjournals.org/cancerrescommun/article-pdf/doi/{doi}/")
    if pmcid:
        if not pmcid.upper().startswith("PMC"):
            pmcid = "PMC" + pmcid
        urls += [
            f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/main.pdf",
            f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/{suffix}.pdf",
            f"https://europepmc.org/articles/{pmcid}?pdf=render",
        ]
    return unique([u for u in urls if u])


REPOS = {
    "10.1016/j.cell.2019.10.007": [
        "https://digitalcommons.wustl.edu/cgi/viewcontent.cgi?article=10906&context=open_access_pubs",
    ],
    "10.1021/ac702422x": [
        "https://figshare.com/ndownloader/files/4643407",
    ],
    "10.1158/2159-8290.CD-13-0219": [
        "https://aacrjournals.org/cancerdiscovery/article-pdf/1108/141373/candisc_3_10_1108.pdf",
    ],
}


def try_url_list(urls: list[str], dest: Path) -> tuple[bool, str]:
    for url in unique(urls):
        if url.endswith(".tar.gz"):
            try:
                pdf = extract_pdf_from_tgz(url)
                if save_pdf(pdf, dest):
                    return True, url
            except Exception:
                pass
            continue
        try:
            data, final = fetch_pdf(url)
            if save_pdf(data, dest):
                return True, final
            if "text/html" in str(data[:20]):
                for m in re.findall(r'href="([^"]+\.pdf[^"]*)"', data.decode("utf-8", "ignore"), re.I):
                    pdf_url = urljoin(final, m)
                    d2, f2 = fetch_pdf(pdf_url)
                    if save_pdf(d2, dest):
                        return True, f2
        except Exception:
            pass
        time.sleep(0.15)
    return False, ""


def playwright_pmc(pmcid: str, dest: Path) -> tuple[bool, str]:
    if not pmcid:
        return False, ""
    if not pmcid.upper().startswith("PMC"):
        pmcid = "PMC" + pmcid
    url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(accept_downloads=True)
            page = ctx.new_page()

            with page.expect_download(timeout=45000) as dl_info:
                page.goto(url, wait_until="networkidle", timeout=90000)
                for sel in [
                    "a[aria-label*='PDF']",
                    "a[title*='PDF']",
                    "a:has-text('PDF')",
                    "a[href*='pdf']",
                ]:
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        loc.first.click()
                        break
            download = dl_info.value
            path = download.path()
            if path:
                data = Path(path).read_bytes()
                if save_pdf(data, dest):
                    browser.close()
                    return True, url
            browser.close()
    except Exception:
        pass
    return False, ""


def load_rows() -> list[dict]:
    with METADATA.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    rows = load_rows()
    new = 0
    print(f"Stage 5: extended download", flush=True)
    for row in rows:
        idx = int(row["№"])
        doi = row["DOI"]
        title = row["Title"]
        year = row.get("Year", "")
        pmcid = row.get("PMCID", "")
        dest = PDF_DIR / (safe_filename(f"{idx:02d}_{year}_{title}") + ".pdf")
        if is_valid_pdf(dest):
            print(f"[{idx}] skip", flush=True)
            continue

        print(f"[{idx}] {doi}", flush=True)
        urls = []
        urls.extend(REPOS.get(doi, []))
        urls.extend(publisher_urls(doi, pmcid))
        urls.extend(pmc_oa_package(pmcid))
        urls.extend(unpaywall_urls(doi))
        time.sleep(0.3)
        urls.extend(openalex_urls(doi))
        time.sleep(0.3)
        urls.extend(core_urls(doi))

        ok, final = try_url_list(urls, dest)
        if not ok and pmcid:
            ok, final = playwright_pmc(pmcid, dest)

        if ok:
            new += 1
            row["PDF status"] = "downloaded"
            row["PDF source"] = "stage5"
            row["PDF URL"] = final
            row["Local PDF"] = str(dest)
            print(f"  -> OK {final[:100]}", flush=True)
        else:
            print("  -> FAIL", flush=True)

    with METADATA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    total = sum(1 for r in rows if r.get("Local PDF") and is_valid_pdf(Path(r["Local PDF"])))
    print(f"\nStage 5 done. New: {new}. Total valid: {total}/38", flush=True)


if __name__ == "__main__":
    main()
