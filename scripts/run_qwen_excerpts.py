#!/usr/bin/env python3
"""Выдержки PubMed/PRIDE/PDC + локальный Qwen (без облачных токенов), затем сайт."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas_agent.config import load_config
from atlas_agent.discovery.filters import build_catalog_index, default_filter_config
from atlas_agent.discovery.repository_text import enrich_existing_report
from atlas_agent.llm_client import is_ollama_available
from atlas_agent.sources.projects_table import load_catalog
from atlas_agent.viz.publish_site import publish_discovery_site


def main() -> int:
    if not is_ollama_available():
        print("Ollama/Qwen is not running. Start: ollama serve && ollama pull qwen2.5:3b")
        return 1
    cfg = load_config()
    llm = dict(cfg.get("llm") or {})
    llm["provider"] = "ollama"
    llm["prefer_cloud"] = False
    cfg = {**cfg, "llm": llm, **default_filter_config()}
    df = load_catalog(cfg)
    index = build_catalog_index(df)
    path = ROOT / "data" / "discovery_history" / "latest.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    print("Qwen local:", llm.get("model") or "qwen2.5:3b")
    print("candidates in:", len(report.get("candidates") or []))
    stats = enrich_existing_report(report, index, cfg=cfg, fetch_pubmed=True, use_llm=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("rescue", stats)
    c = report.get("candidates") or []
    print("candidates out", len(c))
    pubmed = sum(1 for x in c if x.get("excerpt_source") == "pubmed")
    qwen = sum(1 for x in c if str(x.get("abstract_reader") or "").startswith("ollama"))
    print("pubmed excerpts", pubmed, "qwen-read", qwen)
    site = publish_discovery_site(report, ROOT)
    print("site", site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
