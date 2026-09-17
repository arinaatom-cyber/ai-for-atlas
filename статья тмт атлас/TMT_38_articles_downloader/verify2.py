#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, json, re, time, urllib.parse, urllib.request
from pathlib import Path
import fitz

BASE = Path(__file__).resolve().parent
PDF = BASE / "TMT_articles" / "PDF"
rows = list(csv.DictReader((BASE / "TMT_articles/metadata.csv").open(encoding="utf-8-sig")))

def pdf_all_text(path):
    doc = fitz.open(path)
    t = "".join(doc.load_page(i).get_text() for i in range(doc.page_count))
    doc.close()
    return t

def epmc_abstract(doi):
    params = urllib.parse.urlencode({"query": f'DOI:"{doi}"', "format": "json", "resultType": "core", "pageSize": 1})
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + params
    data = json.loads(urllib.request.urlopen(url, timeout=25).read())
    return (data.get("resultList", {}).get("result") or [{}])[0].get("abstractText", "")

def find_context(text, pattern, n=3):
    out = []
    for m in re.finditer(pattern, text, re.I):
        s = max(0, m.start() - 80)
        e = min(len(text), m.end() + 120)
        out.append(re.sub(r"\s+", " ", text[s:e]))
        if len(out) >= n:
            break
    return out

checks = []

# 08 review - user's claims about pooled/reference
f = list(PDF.glob("08_*.pdf"))
if f:
    t = pdf_all_text(f[0])
    for pat in [r"pool", r"reference channel", r"reference sample", r"bridge", r"normalization", r"not universal", r"labeling", r"mixing", r"multiplex"]:
        checks.append({"article": 8, "pattern": pat, "count": len(re.findall(pat, t, re.I)), "examples": find_context(t, pat, 2)})

# 31 GTEx science
f = list(PDF.glob("31_*.pdf"))
if f:
    t = pdf_all_text(f[0])
    for pat in [r"49 tissues", r"54 tissues", r"49 human", r"54 human", r"948 donors", r"948 post"]:
        checks.append({"article": 31, "pattern": pat, "count": len(re.findall(pat, t, re.I)), "examples": find_context(t, pat, 2)})

# Key PDFs with numbers
for pref, pats in {
    "22_": [r"110", r"101", r"adjacent normal", r"NAT"],
    "27_": [r"1,000", r"1000", r"ten cohort", r"10 cohort"],
    "36_": [r"7,171", r"7171", r"11 large"],
    "37_": [r"2,458", r"2458", r"440 sample", r"299"],
    "38_": [r"178", r"15 public", r"12 tissue"],
    "16_": [r"TCGA", r"colorectal", r"rectal", r"colon and rectal"],
}.items():
    f = list(PDF.glob(pref + "*.pdf"))
    if f:
        t = pdf_all_text(f[0])
        for pat in pats:
            checks.append({"article": pref, "pattern": pat, "count": len(re.findall(pat, t, re.I)), "examples": find_context(t, pat, 2)})

# Abstract-only articles
for doi, pats, idx in [
    ("10.1021/ac0262560", [r"two", r"pair", r"dual", r"comparative", r"reporter"], 2),
    ("10.1038/s41596-018-0006-9", [r"MS3", r"multi-notch", r"SPS", r"TMT-10", r"TMT10"], 9),
    ("10.1016/j.cell.2020.08.036", [r"201", r"32", r"14 donor", r"TMT10", r"MS3"], 30),
    ("10.1016/j.cell.2019.12.023", [r"375", r"TMT", r"multiplex", r"16"], 32),
    ("10.1093/nar/gkae1011", [r"42000", r"42,000", r"500", r"534"], 11),
]:
    t = epmc_abstract(doi)
    for pat in pats:
        checks.append({"article": idx, "doi": doi, "pattern": pat, "count": len(re.findall(pat, t, re.I)), "examples": find_context(t, pat, 2)})
    time.sleep(0.15)

(BASE / "TMT_articles" / "verify2.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
print("written", len(checks), "checks")
