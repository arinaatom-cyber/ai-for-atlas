"""HTML QC-отчёт Discovery: candidate / manual-check / rejected."""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path


def _rows(items: list[dict], *, status: str) -> str:
    out = []
    for it in items:
        acc = html.escape(it.get("project_accession") or it.get("accession") or "—")
        title = html.escape((it.get("title") or "")[:120])
        reasons = html.escape("; ".join((it.get("qc_reasons") or it.get("filter_reasons") or [])[:2]))
        sig = it.get("material_signals") or {}
        inc = html.escape(", ".join(sig.get("included") or [])[:80])
        exc = html.escape(", ".join(sig.get("excluded") or [])[:80])
        plex = it.get("tmt_label") or it.get("inferred_plex") or ""
        out.append(
            f"<tr><td><b>{acc}</b></td><td>{title}</td><td>{plex}</td>"
            f"<td>{inc}</td><td>{exc}</td><td>{reasons}</td></tr>"
        )
    if not out:
        return f"<tr><td colspan='6'>Нет записей ({status})</td></tr>"
    return "\n".join(out)


def generate_qc_html(report: dict, out_path: str | Path) -> Path:
    s = report.get("summary") or {}
    cand = report.get("candidates") or report.get("new_projects") or []
    manual = report.get("manual_check") or []
    rejected = report.get("rejected_material") or []
    technical = report.get("filtered_out") or []

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    gen = (report.get("generated_at") or "")[:19].replace("T", " ")

    page = f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"/>
<title>Discovery QC Report</title>
<style>
  body {{ font-family: Segoe UI, sans-serif; background:#0f1419; color:#e7ecf3; margin:0; padding:24px; }}
  h1 {{ color:#6cb6ff; }} h2 {{ color:#3dd68c; margin-top:2rem; }}
  .kpi {{ display:flex; gap:16px; flex-wrap:wrap; margin:16px 0; }}
  .kpi div {{ background:#1a2332; border:1px solid #2a3548; border-radius:8px; padding:12px 18px; }}
  .kpi b {{ font-size:1.4rem; color:#6cb6ff; display:block; }}
  table {{ width:100%; border-collapse:collapse; font-size:.88rem; margin-top:8px; }}
  th,td {{ text-align:left; padding:8px; border-bottom:1px solid #2a3548; vertical-align:top; }}
  th {{ color:#8b9cb3; }} .sub {{ color:#8b9cb3; }}
  .rules {{ background:#1a2332; padding:16px; border-radius:8px; font-size:.9rem; line-height:1.5; }}
</style></head><body>
<h1>Discovery QC Report</h1>
<p class="sub">projects.csv не изменялся · {gen} UTC</p>
<div class="kpi">
  <div><b>{len(cand)}</b>candidate</div>
  <div><b>{len(manual)}</b>requires_manual_check</div>
  <div><b>{len(rejected)}</b>rejected (material)</div>
  <div><b>{len(technical)}</b>filtered (TMT/technical)</div>
</div>
<div class="rules">
<b>Правила материала:</b> Homo sapiens only · tumor tissue / adjacent normal / patient plasma·serum·blood /
human-derived cancer cell lines OK · reject spheroids/organoids-only, PDX/xenograft-only, animal tissue,
non-human cell lines · mixed tissue+organoids → manual check.
</div>
<h2>Candidate ({len(cand)})</h2>
<table><tr><th>ID</th><th>Title</th><th>Plex</th><th>Included</th><th>Excluded</th><th>Notes</th></tr>
{_rows(cand, status="candidate")}</table>
<h2>Requires manual check ({len(manual)})</h2>
<table><tr><th>ID</th><th>Title</th><th>Plex</th><th>Included</th><th>Excluded</th><th>Reason</th></tr>
{_rows(manual, status="manual")}</table>
<h2>Rejected — material ({len(rejected)})</h2>
<table><tr><th>ID</th><th>Title</th><th>Plex</th><th>Included</th><th>Excluded</th><th>Reason</th></tr>
{_rows(rejected, status="rejected")}</table>
</body></html>"""
    out.write_text(page, encoding="utf-8")
    return out


def qc_markdown_summary(report: dict) -> str:
    s = report.get("summary") or {}
    lines = [
        "## QC материала образцов",
        "",
        f"- **Candidate:** {s.get('candidates', 0)}",
        f"- **Requires manual check:** {s.get('manual_check', 0)}",
        f"- **Rejected (material):** {s.get('rejected_material', 0)}",
        f"- **Filtered (technical):** {s.get('filtered_out', 0)}",
        "",
        "Правила: Homo sapiens; tumor/adjacent/plasma/blood/human cancer cell lines; "
        "исключить spheroids/organoids-only, PDX-only, xenograft-only, animal tissue.",
        "",
    ]
    for label, key in (
        ("Manual check", "manual_check"),
        ("Rejected", "rejected_material"),
    ):
        items = report.get(key) or []
        if not items:
            continue
        lines.append(f"### {label} (top 10)")
        lines.append("")
        for it in items[:10]:
            acc = it.get("project_accession") or it.get("accession") or "?"
            rs = "; ".join((it.get("qc_reasons") or [])[:1])
            lines.append(f"- **{acc}** {(it.get('title') or '')[:70]} — {rs}")
        lines.append("")
    return "\n".join(lines)
