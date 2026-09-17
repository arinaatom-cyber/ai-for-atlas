#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_i18n_keys() -> set[str]:
    js = (ROOT / "atlas_agent/viz/site_assets/i18n.js").read_text(encoding="utf-8")
    keys: set[str] = {"brand_title"}
    for block in ("SHARED", "PAGE"):
        m = re.search(rf"const {block} = \{{", js)
        if not m:
            continue
    keys.update(re.findall(r"^\s+(\w+):\s", js, re.M))
    return keys


def audit_html(keys: set[str]) -> dict:
    issues: list[str] = []
    missing_i18n: dict[str, list[str]] = {}
    for hp in sorted((ROOT / "docs").rglob("*.html")):
        text = hp.read_text(encoding="utf-8", errors="replace")
        rel = hp.relative_to(ROOT).as_posix()
        for m in re.finditer(r'data-i18n="([^"]+)"', text):
            k = m.group(1)
            if k not in keys:
                missing_i18n.setdefault(k, []).append(rel)
        for m in re.finditer(r"<button[^>]*>([^<]+)</button>", text):
            frag = m.group(0)
            label = m.group(1).strip()
            if label and "data-i18n" not in frag:
                issues.append(f"{rel}: hardcoded button «{label[:50]}»")
    return {"missing_i18n": missing_i18n, "issues": issues}


def audit_rows(html_path: Path) -> list[str]:
    text = html_path.read_text(encoding="utf-8", errors="replace")
    rows = re.findall(r"<tr[^>]*data-type=[^>]*>.*?</tr>", text, re.S)
    issues: list[str] = []
    for i, row in enumerate(rows, 1):
        typ = re.search(r'data-type="([^"]+)"', row)
        acc = re.search(r'class="cell-mono id-acc"[^>]*><b>([^<]+)</b>', row)
        title = re.search(r'class="cell-title[^"]*"[^>]*>([^<]+)<', row)
        empty_links = "cell-empty" in row and "link-chip" not in row
        hardcoded = []
        for pat, msg in [
            (r">Project<", "link label Project"),
            (r">Data files<", "Data files label"),
            (r">Repo<", "Repo label"),
        ]:
            if re.search(pat, row):
                hardcoded.append(msg)
        if hardcoded:
            issues.append(
                f"row {i} type={typ.group(1) if typ else '?'} "
                f"id={acc.group(1) if acc else '?'}: {', '.join(hardcoded)}"
            )
        if not title and typ and typ.group(1) != "cohort":
            issues.append(f"row {i}: missing title")
    return issues


def audit_latest() -> list[str]:
    latest = json.loads((ROOT / "data/discovery_history/latest.json").read_text(encoding="utf-8"))
    issues: list[str] = []
    for section, key in [
        ("candidate", "candidates"),
        ("manual", "manual_check"),
        ("cohort", "cohort_literature"),
    ]:
        items = latest.get(key) or []
        if key == "candidates":
            items = items or latest.get("new_projects") or []
        for it in items:
            acc = it.get("project_accession") or it.get("accession") or ""
            pmid = it.get("pmid") or ""
            title = (it.get("title") or "")[:60]
            if not title:
                issues.append(f"{section}: no title acc={acc} pmid={pmid}")
            if section == "candidate" and not acc:
                issues.append(f"candidate missing accession: {title}")
    return issues


def main() -> int:
    keys = load_i18n_keys()
    html_audit = audit_html(keys)
    disc = ROOT / "docs/site/discovery.html"
    row_issues = audit_rows(disc) if disc.is_file() else []
    data_issues = audit_latest()

    print("=== i18n keys missing in i18n.js ===")
    for k, files in sorted(html_audit["missing_i18n"].items()):
        print(f"  {k}: {', '.join(files[:3])}")

    print("\n=== HTML button issues ===")
    for x in html_audit["issues"][:20]:
        print(f"  {x}")
    if not html_audit["issues"]:
        print("  (none)")

    print("\n=== Table row hardcoded labels ===")
    for x in row_issues[:30]:
        print(f"  {x}")
    if not row_issues:
        print("  (none)")

    print("\n=== latest.json data issues ===")
    for x in data_issues[:20]:
        print(f"  {x}")
    if not data_issues:
        print("  (none)")

    n_bad = len(html_audit["missing_i18n"]) + len(html_audit["issues"]) + len(row_issues)
    return 1 if n_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
