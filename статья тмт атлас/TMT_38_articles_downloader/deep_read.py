#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, json, re, time, urllib.parse, urllib.request
from pathlib import Path
import fitz

BASE = Path(__file__).resolve().parent
rows = list(csv.DictReader((BASE / "TMT_articles/metadata.csv").open(encoding="utf-8-sig")))

CHECKS = {
    "10.1021/ac0262560": ["two", "dual", "pair", "multiplex", "reporter"],
    "10.1093/nar/gkae1011": ["42000", "42,000", "534", "500", "2024", "2023"],
    "10.1126/science.aaz1776": ["49", "54", "tissue", "948"],
    "10.1016/j.cell.2020.08.036": ["201", "32", "14", "TMT", "MS3", "donor"],
    "10.1038/s41596-018-0006-9": ["MS3", "TMT", "10", "phospho"],
    "10.1002/cbic.201800650": ["pooled", "reference", "bridge", "multiplex", "limitation"],
    "10.1093/nar/gkac1040": ["34233", "34", "2022", "PRIDE", "MassIVE", "iProX"],
}

def fetch_abstract(doi):
    params = urllib.parse.urlencode({"query": f'DOI:"{doi}"', "format": "json", "resultType": "core", "pageSize": 1})
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + params
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=25).read())
        return (data.get("resultList", {}).get("result") or [{}])[0].get("abstractText", "")
    except Exception:
        return ""

def pdf_text(path, pages=20):
    doc = fitz.open(path)
    t = []
    for i in range(min(pages, doc.page_count)):
        t.append(doc.load_page(i).get_text())
    doc.close()
    return "\n".join(t)

out = []
for row in rows:
    doi = row["DOI"]
    idx = int(row["№"])
    local = row.get("Local PDF", "")
    text = ""
    source = ""
    if local and Path(local).exists():
        text = pdf_text(Path(local), pages=25)
        source = "pdf_full"
    if len(text) < 500:
        text = fetch_abstract(doi)
        source = "abstract"
    snippet = re.sub(r"\s+", " ", text)
    hits = {}
    if doi in CHECKS:
        for k in CHECKS[doi]:
            hits[k] = bool(re.search(re.escape(k), snippet, re.I))
    out.append({"idx": idx, "doi": doi, "title": row["Title"], "source": source, "len": len(snippet), "hits": hits, "text": snippet[:5000]})
    print(idx, source, len(snippet), hits if hits else "")
    time.sleep(0.12)

(BASE / "TMT_articles" / "deep_read.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
