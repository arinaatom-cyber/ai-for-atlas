#!/usr/bin/env python3
"""Dump discovery scan results with proteome vs phospho tier breakdown."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def file_tier(item: dict) -> tuple[str, str]:
    """Tier label from data_availability.omics_layer (committed pipeline field)."""
    da = item.get("data_availability") or {}
    layer = da.get("omics_layer") or ""
    status = da.get("status") or ""
    proteome = da.get("proteome_files") or []
    phospho = da.get("phospho_files") or []
    qf = da.get("quant_files") or []

    if layer == "protein" or proteome:
        tier = "PROTEOME"
        top = proteome[0] if proteome else (qf[0] if qf else "")
    elif layer == "phospho_only" or status == "phospho_table":
        tier = "PHOSPHO-ONLY"
        top = phospho[0] if phospho else (qf[0] if qf else "")
    elif layer == "mixed":
        tier = "MIXED"
        top = proteome[0] if proteome else (qf[0] if qf else "")
    elif status == "raw_only":
        tier = "RAW-ONLY"
        top = qf[0] if qf else ""
    elif status == "no_files":
        tier = "NO-FILES"
        top = ""
    else:
        tier = da.get("label") or layer or "unknown"
        top = qf[0] if qf else ""
    return tier, top


def main() -> None:
    rep = json.loads((ROOT / "data/discovery_history/latest.json").read_text(encoding="utf-8"))
    s = rep.get("summary") or {}
    cands = rep.get("candidates") or []

    tiers: dict[str, int] = {}
    for c in cands:
        t, _ = file_tier(c)
        tiers[t] = tiers.get(t, 0) + 1

    print("=" * 72)
    print("CANDIDATES (%d) — tier breakdown: %s" % (len(cands), tiers))
    print("=" * 72)
    for i, c in enumerate(cands, 1):
        acc = c.get("accession") or c.get("project_accession") or ""
        tier, top = file_tier(c)
        mat = ",".join((c.get("material_signals") or {}).get("included") or [])[:2]
        title = (c.get("title") or c.get("projectTitle") or "")[:95]
        plex = c.get("tmt_label") or c.get("inferred_plex") or ""
        frac = c.get("analytical_fraction") or ""
        print(f"{i:2}. {acc:14} | {plex:12} | {tier:12} | {c.get('source', '')}")
        print(f"    {title}")
        if frac:
            print(f"    PDC fraction: {frac}")
        if mat:
            print(f"    material: {mat}")
        if top:
            print(f"    file: {top[:90]}")
        note = (c.get("finding_note") or "")[:130]
        if note:
            print(f"    note: {note}")
        print()

    print("=" * 72)
    print("MANUAL CHECK (%d)" % len(rep.get("manual_check") or []))
    print("=" * 72)
    for i, m in enumerate(rep.get("manual_check") or [], 1):
        acc = m.get("accession") or ("PMID:" + str(m.get("pmid") or ""))
        title = (m.get("title") or "")[:80]
        reasons = (m.get("filter_reasons") or m.get("qc_reasons") or [])[:2]
        fit = (m.get("abstract_ai") or {}).get("atlas_fit") or m.get("atlas_fit") or ""
        print(f"{i:2}. {acc} | fit={fit}")
        print(f"    {title}")
        if reasons:
            print(f"    reason: {'; '.join(str(x) for x in reasons)}")
        print()

    print("=" * 72)
    print("REJECTED MATERIAL (%d)" % len(rep.get("rejected_material") or []))
    print("=" * 72)
    for i, m in enumerate(rep.get("rejected_material") or [], 1):
        acc = m.get("accession") or ""
        reasons = (m.get("qc_reasons") or m.get("filter_reasons") or [])[:2]
        print(f"{i}. {acc}: {'; '.join(str(x) for x in reasons)}")

    print()
    print("=" * 72)
    print("FILTERED OUT (first 20 of %s)" % s.get("filtered_out"))
    phospho_n = s.get("phospho_only_filtered", "?")
    print("  phospho-only filtered (files/metadata): %s" % phospho_n)
    print("=" * 72)
    for m in (rep.get("filtered_out") or [])[:20]:
        acc = m.get("accession") or m.get("pmid") or ""
        reasons = (m.get("filter_reasons") or [])[:2]
        print(f"- {acc}: {'; '.join(str(x) for x in reasons)[:110]}")


if __name__ == "__main__":
    main()
