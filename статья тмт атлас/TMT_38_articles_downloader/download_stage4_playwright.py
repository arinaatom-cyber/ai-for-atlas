#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 4: Playwright browser downloads for PMC and publisher pages."""

from __future__ import annotations

import csv
import re
import time
import unicodedata
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "TMT_articles"
PDF_DIR = OUTPUT / "PDF"
METADATA = OUTPUT / "metadata.csv"
MIN_SIZE = 200_000  # reject tiny/wrong PDFs


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


def load_rows() -> list[dict]:
    with METADATA.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def candidate_urls(row: dict) -> list[str]:
    doi = row["DOI"]
    pmcid = (row.get("PMCID") or "").strip()
    urls = [row.get("DOI link", f"https://doi.org/{doi}")]

    if pmcid:
        if not pmcid.upper().startswith("PMC"):
            pmcid = "PMC" + pmcid
        urls.insert(0, f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/")
        urls.insert(0, f"https://europepmc.org/article/MED/{row.get('PMID','')}")

    if doi.startswith("10.1371/"):
        urls.insert(0, f"https://journals.plos.org/ploscompbiol/article?id={doi}")
    if doi.startswith("10.3390/"):
        urls.insert(0, f"https://doi.org/{doi}")
    if doi.startswith("10.1093/nar/"):
        urls.insert(0, f"https://doi.org/{doi}")

    return urls


def try_download(page, url: str, destination: Path) -> tuple[bool, str]:
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if not response:
            return False, "no response"

        # direct PDF
        body = response.body()
        if body[:4] == b"%PDF" and len(body) >= MIN_SIZE:
            destination.write_bytes(body)
            return True, url

        # click download/pdf buttons
        selectors = [
            "a[href*='.pdf']",
            "a[title*='PDF']",
            "a:has-text('Download PDF')",
            "a:has-text('PDF')",
            "button:has-text('PDF')",
            "a[aria-label*='PDF']",
            "#downloadPdf",
            ".article-pdf-link",
        ]
        for selector in selectors:
            loc = page.locator(selector)
            count = loc.count()
            for i in range(min(count, 5)):
                href = loc.nth(i).get_attribute("href")
                if href and ".pdf" in href.lower():
                    target = page.urljoin(href) if hasattr(page, "urljoin") else href
                    if not target.startswith("http"):
                        from urllib.parse import urljoin
                        target = urljoin(page.url, href)
                    try:
                        pdf_resp = page.context.request.get(target, timeout=60000)
                        data = pdf_resp.body()
                        if data[:4] == b"%PDF" and len(data) >= MIN_SIZE:
                            destination.write_bytes(data)
                            return True, target
                    except Exception:
                        pass

        # Europe PMC render endpoint from page
        html = page.content()
        for match in re.findall(r'(https?://[^\"\']+(?:pdf|render)[^\"\']*)', html, re.I):
            if "recruitment" in match.lower():
                continue
            try:
                pdf_resp = page.context.request.get(match, timeout=60000)
                data = pdf_resp.body()
                if data[:4] == b"%PDF" and len(data) >= MIN_SIZE:
                    destination.write_bytes(data)
                    return True, match
            except Exception:
                pass
    except Exception as exc:
        return False, str(exc)
    return False, "no pdf found"


def main() -> None:
    rows = load_rows()
    pending = []
    for row in rows:
        local = row.get("Local PDF", "")
        if row.get("PDF status") == "downloaded" and local and is_valid_pdf(Path(local)):
            continue
        index = int(row["№"])
        destination = PDF_DIR / (safe_filename(f"{index:02d}_{row.get('Year','')}_{row['Title']}") + ".pdf")
        if is_valid_pdf(destination):
            row["PDF status"] = "downloaded"
            row["Local PDF"] = str(destination)
            continue
        pending.append((row, destination))

    print(f"Stage 4 Playwright: {len(pending)} articles", flush=True)
    new_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            accept_downloads=True,
        )
        page = context.new_page()

        for row, destination in pending:
            index = int(row["№"])
            print(f"[{index}] {row['DOI']}", flush=True)
            ok = False
            final = ""
            for url in candidate_urls(row):
                ok, final = try_download(page, url, destination)
                if ok:
                    break
                time.sleep(0.3)

            if ok:
                new_count += 1
                row["PDF status"] = "downloaded"
                row["PDF source"] = "stage4 playwright"
                row["PDF URL"] = final
                row["Local PDF"] = str(destination)
                print(f"  -> OK {final}", flush=True)
            else:
                print(f"  -> FAIL {final}", flush=True)

        browser.close()

    with METADATA.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    total = sum(1 for r in rows if r.get("PDF status") == "downloaded" and r.get("Local PDF") and is_valid_pdf(Path(r["Local PDF"])))
    print(f"\nStage 4 done. New: {new_count}. Valid total: {total}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
