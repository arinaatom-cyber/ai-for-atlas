#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 3: Cell/Elsevier PII PDF URLs, PMC via browser-like flow, repositories."""

from __future__ import annotations

import csv
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote, urljoin

from curl_cffi import requests

EMAIL = "arina.atom@gmail.com"
BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "TMT_articles"
PDF_DIR = OUTPUT / "PDF"
METADATA = OUTPUT / "metadata.csv"
TIMEOUT = 50
SLEEP = 0.2
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
    if data.startswith(b"%PDF"):
        destination.write_bytes(data)
        return True
    return False


def unique(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def pii_to_cell_pdf(pii: str, journal: str = "cell") -> str:
    # S0092867420307443 -> S0092-8674(20)30744-3
    m = re.match(r"(S\d{4})(\d{4})(\d{2})(\d{3,4})(\d?)", pii, re.I)
    if not m:
        return ""
    prefix, issn, year2, middle, suffix = m.groups()
    suffix = suffix or ""
    return f"https://www.cell.com/{journal}/pdf/{prefix}-{issn}({year2}){middle}{'-' + suffix if suffix else ''}.pdf"


def resolve_elsevier_pii(doi: str) -> list[str]:
    urls = []
    try:
        response = SESSION.get(
            f"https://doi.org/{doi}",
            timeout=TIMEOUT,
            allow_redirects=True,
            headers={"Accept": "text/html"},
        )
        final = str(response.url)
        pii_match = re.search(r"pii/([A-Z0-9()]+)", final, re.I)
        if pii_match:
            pii = pii_match.group(1)
            journal = "ccell" if "/j.ccell." in doi else "cell"
            cell_pdf = pii_to_cell_pdf(pii, journal=journal)
            if cell_pdf:
                urls.append(cell_pdf)
            urls.append(f"https://linkinghub.elsevier.com/retrieve/pii/{pii}")
            urls.append(f"http://www.cell.com/article/{pii}/pdf")
    except Exception:
        pass
    return urls


def unpaywall_all(doi: str) -> list[str]:
    url = f"https://api.unpaywall.org/v2/{quote(doi, safe='')}?email={quote(EMAIL)}"
    try:
        payload = SESSION.get(url, timeout=TIMEOUT).json()
    except Exception:
        return []
    urls = []
    for location in payload.get("oa_locations", []):
        for key in ("url_for_pdf", "url", "url_for_landing_page"):
            value = location.get(key) or ""
            if value:
                urls.append(value)
    return unique(urls)


def pmc_from_page(pmcid: str) -> list[str]:
    if not pmcid:
        return []
    if not pmcid.upper().startswith("PMC"):
        pmcid = "PMC" + pmcid
    page = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    urls = []
    try:
        html = SESSION.get(page, timeout=TIMEOUT).text
        for match in re.findall(r'href="([^"]+)"', html):
            if ".pdf" in match.lower() or "/pdf/" in match.lower():
                urls.append(urljoin(page, match))
        meta = re.search(r'name="citation_pdf_url"\s+content="([^"]+)"', html)
        if meta:
            urls.append(meta.group(1))
    except Exception:
        pass
    return unique(urls)


def known_repository_urls(doi: str) -> list[str]:
    mapping = {
        "10.1016/j.cell.2019.10.007": [
            "https://digitalcommons.wustl.edu/open_access_pubs/9899/",
            "https://digitalcommons.wustl.edu/cgi/viewcontent.cgi?article=10906&context=open_access_pubs",
        ],
        "10.1038/nature18003": [
            "https://nrs.harvard.edu/urn-3:HUL.InstRepos:29626102",
        ],
        "10.1021/ac702422x": [
            "https://figshare.com/articles/journal_contribution/Relative_Quantification_of_Proteins_in_Human_Cerebrospinal_Fluids_by_MS_MS_Using_6_Plex_Isobaric_Tags/2944618/1/files/4643407.pdf",
        ],
        "10.1158/2159-8290.CD-13-0219": [
            "https://cancerdiscovery.aacrjournals.org/content/candisc/3/10/1108.full.pdf",
        ],
    }
    return mapping.get(doi, [])


def try_candidates(candidates: list[str], destination: Path) -> tuple[bool, str]:
    for url in unique(candidates):
        try:
            response = SESSION.get(
                url,
                timeout=TIMEOUT,
                allow_redirects=True,
                headers={"Referer": "https://scholar.google.com/"},
            )
            if save_pdf(response.content, destination):
                return True, str(response.url)
            # repository HTML pages sometimes link to PDF
            if "text/html" in response.headers.get("content-type", ""):
                for match in re.findall(r'href="([^"]+\.pdf[^"]*)"', response.text, re.I):
                    pdf_url = urljoin(str(response.url), match)
                    pdf_resp = SESSION.get(pdf_url, timeout=TIMEOUT, allow_redirects=True)
                    if save_pdf(pdf_resp.content, destination):
                        return True, str(pdf_resp.url)
        except Exception:
            pass
        time.sleep(0.1)
    return False, ""


def load_rows() -> list[dict]:
    with METADATA.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    rows = load_rows()
    new_count = 0
    print(f"Stage 3: {len(rows)} articles", flush=True)

    for row in rows:
        if row.get("PDF status") == "downloaded":
            local = row.get("Local PDF", "")
            if local and is_valid_pdf(Path(local)):
                continue

        index = int(row["№"])
        doi = row["DOI"]
        title = row["Title"]
        year = row.get("Year", "")
        pmcid = row.get("PMCID", "")
        destination = PDF_DIR / (safe_filename(f"{index:02d}_{year}_{title}") + ".pdf")

        if is_valid_pdf(destination):
            row["PDF status"] = "downloaded"
            row["Local PDF"] = str(destination)
            continue

        print(f"[{index}] {doi}", flush=True)
        candidates = []
        candidates.extend(known_repository_urls(doi))
        candidates.extend(resolve_elsevier_pii(doi))
        candidates.extend(pmc_from_page(pmcid))
        candidates.extend(unpaywall_all(doi))
        time.sleep(SLEEP)

        if doi.startswith("10.1016/j."):
            journal = "ccell" if "ccell" in doi else "cell"
            candidates.append(f"http://www.{journal}.com/article/{doi.split('/')[-1]}/pdf")

        ok, final_url = try_candidates(candidates, destination)
        if ok:
            new_count += 1
            row["PDF status"] = "downloaded"
            row["PDF source"] = "stage3"
            row["PDF URL"] = final_url
            row["Local PDF"] = str(destination)
            print(f"  -> OK {final_url}", flush=True)
        else:
            print("  -> FAIL", flush=True)

    with METADATA.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    total = sum(1 for r in rows if r.get("PDF status") == "downloaded")
    print(f"\nStage 3 done. New: {new_count}. Total: {total}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
