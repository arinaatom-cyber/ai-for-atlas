"""Freeze a Discovery snapshot (checksums + git + config; no secrets)."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atlas_agent.config import load_config
from atlas_agent.discovery.catalog_profile import build_catalog_profile
from atlas_agent.discovery.methods_manifest import build_methods_manifest
from atlas_agent.sources.projects_table import load_projects_table
from atlas_agent.viz.export_flat_candidates import write_candidates_csv


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    return (r.stdout or "").strip() if r.returncode == 0 else ""


def _llm_discovery_snapshot(cfg: dict) -> dict:
    disc = cfg.get("discovery") or {}
    llm = cfg.get("llm") or {}
    return {
        "discovery": {
            "year_from": disc.get("year_from"),
            "year_to": disc.get("year_to"),
            "abstract_llm": disc.get("abstract_llm"),
            "abstract_llm_max": disc.get("abstract_llm_max"),
            "search_mode": disc.get("search_mode"),
            "filters": disc.get("filters"),
        },
        "llm": {
            "enabled": llm.get("enabled"),
            "provider": llm.get("provider"),
            "model": llm.get("model"),
            "prefer_cloud": llm.get("prefer_cloud"),
            "base_url": llm.get("base_url"),
        },
    }


def freeze_release(dest: Path | None = None) -> Path:
    cfg = load_config()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dest = dest or (ROOT / "data" / "releases" / stamp)
    dest.mkdir(parents=True, exist_ok=True)

    latest = ROOT / "data" / "discovery_history" / "latest.json"
    report = json.loads(latest.read_text(encoding="utf-8")) if latest.is_file() else {}
    csv_path = ROOT / "data" / "projects.csv"
    df = load_projects_table(str(csv_path)) if csv_path.is_file() else None
    profile = build_catalog_profile(df) if df is not None else {}
    manifest = build_methods_manifest(report, cfg)
    manifest["catalog_profile"] = {
        "n_rows": profile.get("n_rows"),
        "n_unique_ids": profile.get("n_unique_ids"),
        "organ_counts": profile.get("organ_counts"),
        "databases": profile.get("databases"),
    }

    if latest.is_file():
        shutil.copy2(latest, dest / "latest.json")
    if csv_path.is_file():
        shutil.copy2(csv_path, dest / "projects.csv")
    write_candidates_csv(report.get("candidates") or [], dest / "candidates.csv")
    (dest / "methods_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (dest / "config_snapshot.json").write_text(
        json.dumps(_llm_discovery_snapshot(cfg), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sums = []
    for p in sorted(dest.iterdir()):
        if p.is_file() and p.name != "SHA256SUMS.txt":
            sums.append(f"{_sha256(p)}  {p.name}")
    (dest / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    commit = _git_head()
    s = report.get("summary") or {}
    release = (
        f"Discovery snapshot\n"
        f"Date (UTC): {stamp}\n"
        f"git: {commit}\n"
        f"Scan: {report.get('generated_at') or 'n/a'}\n"
        f"Catalog rows: {profile.get('n_rows')}\n"
        f"candidates={s.get('candidates')} filtered_out={s.get('filtered_out')} "
        f"already_in_catalog={s.get('already_in_catalog')}\n"
        f"LLM: {cfg.get('llm', {}).get('provider')} / {cfg.get('llm', {}).get('model')}\n"
    )
    (dest / "RELEASE.txt").write_text(release, encoding="utf-8")
    return dest


def main() -> int:
    dest = freeze_release()
    print(f"Frozen release: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
