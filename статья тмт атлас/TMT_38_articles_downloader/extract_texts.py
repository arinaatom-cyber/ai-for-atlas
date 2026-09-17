#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import fitz

BASE = Path(__file__).resolve().parent
PDF_DIR = BASE / "TMT_articles" / "PDF"
rows = list(csv.DictReader((BASE / "TMT_articles" / "metadata.csv").open(encoding="utf-8-sig")))


def fetch_abstract(doi: str) -> str:
    params = urllib.parse.urlencode({
        "query": f'DOI:"{doi}"',
        "format": "json",
        "resultType": "core",
        "pageSize": 1,
    })
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + params
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=20).read())
        result = (data.get("resultList", {}).get("result") or [{}])[0]
        return result.get("abstractText", "") or ""
    except Exception:
        return ""


def extract_pdf_text(path: Path, pages: int = 4) -> str:
    doc = fitz.open(path)
    chunks = []
    for i in range(min(pages, doc.page_count)):
        chunks.append(doc.load_page(i).get_text())
    doc.close()
    return "\n".join(chunks)


out = []
for row in rows:
    idx = int(row["№"])
    doi = row["DOI"]
    title = row["Title"]
    local = row.get("Local PDF", "")
    source = "abstract_api"
    text = ""
    if local and Path(local).exists():
        text = extract_pdf_text(Path(local))
        source = "pdf"
    if len(text.strip()) < 200:
        text = fetch_abstract(doi)
        source = "abstract_api"
    snippet = re.sub(r"\s+", " ", text).strip()[:3000]
    out.append({"idx": idx, "doi": doi, "title": title, "source": source, "text": snippet})
    print(idx, source, len(snippet), flush=True)
    time.sleep(0.15)

(BASE / "TMT_articles" / "article_texts.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("saved", len(out))
