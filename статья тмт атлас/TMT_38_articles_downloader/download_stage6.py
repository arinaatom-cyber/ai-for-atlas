#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6: Europe PMC + PMC browser session + MDPI for open-access articles."""

from __future__ import annotations

import csv
import re
import time
import unicodedata
from pathlib import Path

from curl_cffi import requests
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
PDF_DIR = BASE / "TMT_articles" / "PDF"
METADATA = BASE / "TMT_articles" / "metadata.csv"
MIN_SIZE = 200_000

# приоритет: gold/green OA с PMCID
TARGETS = [
    10, 11, 13,  # NAR gold
    6, 7, 9, 12,  # Nature Methods green
    15, 17, 24, 33, 35,  # PMC OA
    4, 30, 32,  # доп. PMC
    14, 34,  # hybrid OA
]


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
    if data.startswith(b"%PDF") and len(data) >= MIN_SIZE:
        dest.write_bytes(data)
        return True
    return False


def europe_pmc_urls(pmcid: str, pmid: str, doi: str) -> list[str]:
    if pmcid and not pmcid.upper().startswith("PMC"):
        pmcid = "PMC" + pmcid
    suffix = doi.split("/")[-1]
    urls = []
    if pmcid:
        urls += [
            f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf",
            f"https://europepmc.org/articles/{pmcid}/pdf",
            f"https://europepmc.org/articles/{pmcid}?pdf=render",
        ]
    if pmid:
        urls.append(f"https://europepmc.org/article/MED/{pmid}")
    if doi.startswith("10.3390/"):
        part = suffix.rsplit(".", 1)
        if len(part) == 2:
            urls.append(f"https://www.mdpi.com/{part[0]}/{part[1]}/pdf")
    return urls


def browser_fetch(page, url: str) -> bytes:
    try:
        result = page.evaluate(
            """async (url) => {
                const r = await fetch(url, {credentials: 'include'});
                const buf = await r.arrayBuffer();
                return Array.from(new Uint8Array(buf));
            }""",
            url,
        )
        return bytes(result)
    except Exception:
        return b""


def try_playwright(row: dict, dest: Path) -> tuple[bool, str]:
    doi = row["DOI"]
    pmcid = row.get("PMCID", "")
    pmid = row.get("PMID", "")
    urls = europe_pmc_urls(pmcid, pmid, doi)
    if pmid:
        urls.insert(0, f"https://europepmc.org/article/MED/{pmid}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        for url in urls:
            try:
                page.goto(url, wait_until="networkidle", timeout=90000)

                # прямой PDF-ответ
                for pdf_url in [
                    url,
                    page.url,
                ]:
                    data = browser_fetch(page, pdf_url)
                    if save_pdf(data, dest):
                        browser.close()
                        return True, pdf_url

                # ссылки на PDF на странице
                links = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => e.href).filter(h => /pdf|render|download/i.test(h))",
                )
                for link in links[:8]:
                    data = browser_fetch(page, link)
                    if save_pdf(data, dest):
                        browser.close()
                        return True, link

                # кнопки PDF
                for sel in [
                    "a[title*='PDF']",
                    "a:has-text('Download PDF')",
                    "a:has-text('PDF')",
                    "button:has-text('PDF')",
                ]:
                    loc = page.locator(sel)
                    if loc.count() == 0:
                        continue
                    try:
                        with page.expect_download(timeout=20000) as dl_info:
                            loc.first.click()
                        dl = dl_info.value
                        tmp = dl.path()
                        if tmp:
                            data = Path(tmp).read_bytes()
                            if save_pdf(data, dest):
                                browser.close()
                                return True, page.url
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(0.5)

        browser.close()
    return False, ""


def core_fetch(doi: str, dest: Path) -> tuple[bool, str]:
    sess = requests.Session(impersonate="chrome120")
    url = f"https://api.core.ac.uk/v3/search/works?q=doi:{doi}"
    try:
        data = sess.get(url, timeout=30).json()
        for item in data.get("results", []):
            dl = item.get("downloadUrl")
            if not dl:
                continue
            content = sess.get(dl, timeout=90).content
            if save_pdf(content, dest):
                return True, dl
    except Exception:
        pass
    return False, ""


def load_rows() -> list[dict]:
    with METADATA.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    by_idx = {int(r["№"]): r for r in rows}
    return [by_idx[i] for i in TARGETS if i in by_idx]


def main() -> None:
    targets = load_rows()
    all_rows = list(csv.DictReader(METADATA.open(encoding="utf-8-sig", newline="")))
    new = 0
    print(f"Stage 6: {len(targets)} open-access targets", flush=True)

    for row in targets:
        idx = int(row["№"])
        dest = PDF_DIR / (safe_filename(f"{idx:02d}_{row.get('Year','')}_{row['Title']}") + ".pdf")
        if is_valid_pdf(dest):
            print(f"[{idx}] skip", flush=True)
            continue

        print(f"[{idx}] {row['DOI']}", flush=True)
        ok, src = try_playwright(row, dest)
        if not ok:
            ok, src = core_fetch(row["DOI"], dest)

        if ok:
            new += 1
            row["PDF status"] = "downloaded"
            row["PDF source"] = "stage6"
            row["PDF URL"] = src
            row["Local PDF"] = str(dest)
            print(f"  -> OK {src[:90]}", flush=True)
        else:
            print("  -> FAIL", flush=True)

    by_num = {int(r["№"]): r for r in all_rows}
    for row in targets:
        by_num[int(row["№"])] = row

    with METADATA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_rows[0].keys())
        w.writeheader()
        w.writerows([by_num[int(r["№"])] for r in all_rows])

    import subprocess
    subprocess.run(["python", "finalize_status.py"], cwd=BASE, check=False)
    print(f"\nStage 6 done. New: {new}", flush=True)


if __name__ == "__main__":
    main()
